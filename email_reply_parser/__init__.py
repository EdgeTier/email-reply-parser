"""
    email_reply_parser is a python library port of GitHub's Email Reply Parser.

    For more information, visit https://github.com/zapier/email-reply-parser
"""

import re
from typing import Iterable, Optional, List, Dict, Union
import unidecode

UNIDECODE_EXCEPTIONS = {
    "€": "__EURO__",
    "$": "__USD__",
    "£": "__POUND__",
    "¥": "__YEN__",
    "元": "__YUAN__",
    "₹": "__RUPEE__",
    "C$": "__CAD__",
    "A$": "__AUD__",
    "CHF": "__CHF__",
    "₩": "__WON__"
}


class EmailReplyParser(object):
    """ Represents an email message that is parsed.
    """
    # Header lines found in quoted or forwarded header blocks that ``EmailMessage.HEADER_REGEX`` does not recognise,
    # in the plain, ``*X:*`` and ``**X:**`` forms.
    EXTRA_HEADER_REGEX = re.compile(r"^\**(Date|Cc|Bcc|Received|Reply-To|Importance)\**:")
    # A short custom ``Label:`` field inside a header block (e.g. ``Ref ID: 123`` or ``Ref ID:123``). A colon followed
    # by ``//`` is a URL scheme, not a label.
    HEADER_LABEL_REGEX = re.compile(r"^[A-Z][\w-]*( [\w-]+){0,3}:(?!//)")
    EMAIL_ADDRESS_REGEX = re.compile(r"[\w.+'-]+@[\w-]+(\.[\w-]+)+")
    # The one boundary marker that is a forward rather than a reply, e.g. ``---------- Forwarded message ---------``.
    FORWARD_MARKER_REGEX = re.compile(r"^-+\s?Forwarded.?Message", flags=re.IGNORECASE)
    # ``EmailMessage.HEADER_REGEX`` keywords that name the sender of a quoted message.
    SENDER_HEADER_KEYWORDS = frozenset(
        ("From", "Da", "Från", "Fran", "Von", "Lähettäjä", "Lahettaja", "Fra", "De", "De la", "Από το", "من")
    )

    @staticmethod
    def read(text, *, own_domains: Optional[Union[str, Iterable[str]]] = None):
        """
        Factory method that splits email into list of fragments.

        When the parsed reply is blank, or holds only divider and "Sent from ..." lines, the email is usually a forward
        or quote sent with no new text above it. The boundary at the top of the body is then stripped and the rest
        parsed again, so the forwarded message is kept as the reply.

        Only a boundary with no sender line, or one carrying a ``Forwarded message`` marker, is kept by default: a
        quote marker (``On ... wrote:``) or a divider above a header block is how Gmail and Outlook write a reply, so
        the message below it is usually the other side's. Those are kept only when ``own_domains`` is given and the
        sender is outside them.

        :param text: A string email body.
        :param own_domains: A sender email domain, or a list of them, belonging to the receiving side (e.g. the support
        mailbox). A quoted or forwarded message sent from one of these domains or a subdomain of one, or whose sender
        line carries no email address, is never kept in place of a blank reply.
        :return: An EmailMessage instance.
        """
        message = EmailMessage(text).read()
        if EmailReplyParser._has_content(message.reply):
            return message

        domains = EmailReplyParser._normalise_own_domains(own_domains)
        remainder, sender_line, forwarded = EmailReplyParser._strip_leading_boundary(text)
        if sender_line is not None:
            if not forwarded and not domains:
                return message
            if EmailReplyParser._is_own_sender(sender_line, domains):
                return message

        retry = EmailMessage(remainder).read()
        return retry if EmailReplyParser._has_content(retry.reply) else message

    @staticmethod
    def parse_reply(text, *, own_domains: Optional[Union[str, Iterable[str]]] = None):
        """
        Provides the reply portion of email.

        :param text: A string email body.
        :param own_domains: Sender email domains belonging to the receiving side; see ``read``.
        :return: The reply body message.
        """
        return EmailReplyParser.read(text, own_domains=own_domains).reply

    @staticmethod
    def cut_off_at_signature(body: str, include: Optional[bool] = True, word_limit: Optional[int] = 1000, *,
                             own_domains: Optional[Union[str, Iterable[str]]] = None):
        """
        Remove the signature section from an email, and use the email Reply Parser to try to remove any
        "thread" content.
        Languages supported: English, French, German, Romanian, Spanish, Italian.
        :param body: The email string to be parsed and cleaned.
        :param include: Boolean variable that determines whether an email is cut-off before the signature or
        after. Default True.
        :param word_limit: If we set the word-limit to None the string will not be split and line breaks will
        be retained. If a word-limit is set, the email will be cut-off after that limit if a signature is not
        found before that point. Default = 100.
        :param own_domains: Sender email domains belonging to the receiving side; see ``EmailReplyParser.read``.
        :return: The cleaned reply body, cut off at the signature and stripped of surrounding whitespace.
        """
        parsed_email = EmailReplyParser.parse_reply(body, own_domains=own_domains)
        cleaned_email = EmailMessage.clean_email_content(parsed_email, include, word_limit)
        return cleaned_email.strip()

    @staticmethod
    def _strip_leading_boundary(text: str):
        """
        Strip the forward or quote boundary at the top of an email body: a leading run of blank, divider and
        "Sent from ..." lines, quote markers (e.g. ``On ... wrote:``) and header blocks, including blank lines between
        nested blocks. A custom ``Label:`` line or a wrapped address-list line belongs to a header block only when a
        recognised header follows it with no blank line between, so such a line below the block stays in the body.

        :param text: A string email body.
        :return: The text below the boundary; the first line in the boundary naming a sender (a ``From:``-style
        header joined with any address lines wrapped below it, or a quote marker), or None if the boundary has none;
        and whether the boundary holds a ``Forwarded message`` marker.
        """
        lines = text.replace('\r\n', '\n').split('\n')
        sender_line = None
        seen_header = False
        forwarded = False
        index = 0
        while index < len(lines):
            line = lines[index].strip()
            block_end, block_sender_line = EmailReplyParser._consume_header_block(lines, index, seen_header)
            if block_end > index:
                sender_line = sender_line or block_sender_line
                seen_header = True
                index = block_end
                continue
            if seen_header and EmailReplyParser._is_header_continuation(line):
                # A label or address line with no header below it is body text, so the boundary ends above it.
                break

            if EmailReplyParser.FORWARD_MARKER_REGEX.match(line):
                forwarded = True
                index += 1
                continue
            if not line or EmailReplyParser._is_divider_or_device_line(line):
                index += 1
                continue
            # A quote marker may wrap onto a second line (e.g. ``On ... <address>\nwrote:``).
            marker = EmailMessage.MULTI_QUOTE_HDR_REGEX.match('\n'.join(lines[index:index + 2]).lstrip())
            if not marker:
                break
            sender_line = sender_line or marker.group(0).strip()
            index += marker.group(0).rstrip().count('\n') + 1
        return '\n'.join(lines[index:]), sender_line, forwarded

    @staticmethod
    def _consume_header_block(lines, start: int, after_header: bool):
        """
        Consume one header block starting at ``start``: a run of header lines and the custom ``Label:`` or wrapped
        address-list lines between them. A run of such lines below the last header line is not part of the block.

        :param lines: The lines of the email body.
        :param start: The index of the line to start from.
        :param after_header: Whether a header block has already been consumed above ``start``, so that the block may
        open with a label or address line.
        :return: The index just below the block's last header line (``start`` if it has none), and the block's sender
        line: its first ``From:``-style header joined with the label or address lines wrapped below it, or None.
        """
        block_end = start
        sender_line = None
        # Lines wrapped below the sender header, joined to it once the next header line shows they are in the block.
        sender_wrap = None
        index = start
        while index < len(lines):
            line = lines[index].strip()
            header = EmailMessage.HEADER_REGEX.match(line)
            if header or EmailReplyParser.EXTRA_HEADER_REGEX.match(line):
                if sender_wrap:
                    sender_line = ' '.join([sender_line] + sender_wrap)
                sender_wrap = None
                if sender_line is None and header and header.group(4) in EmailReplyParser.SENDER_HEADER_KEYWORDS:
                    sender_line, sender_wrap = line, []
                index += 1
                block_end = index
            elif (after_header or block_end > start) and EmailReplyParser._is_header_continuation(line):
                if sender_wrap is not None:
                    sender_wrap.append(line)
                index += 1
            else:
                break
        return block_end, sender_line

    @staticmethod
    def _is_header_continuation(line: str) -> bool:
        """
        Whether a stripped line may continue a header block: a short custom ``Label:`` field, or a wrapped
        address-list line with no colon.

        :param line: The stripped line to check.
        :return: True if the line may continue a header block.
        """
        return bool(line) and bool(EmailReplyParser.HEADER_LABEL_REGEX.match(line) or (
            ':' not in line and EmailReplyParser.EMAIL_ADDRESS_REGEX.search(line)))

    @staticmethod
    def _normalise_own_domains(own_domains) -> list:
        """
        Normalise the ``own_domains`` argument into a list of lower-case domain names.

        :param own_domains: A domain string, an iterable of domain strings, or None. ``None`` and empty entries are
        skipped, and a leading ``@``, surrounding whitespace and letter case are ignored.
        :return: The normalised domains, empty if none were given.
        """
        if isinstance(own_domains, str):
            own_domains = [own_domains]
        domains = [(domain or '').strip().lstrip('@').strip().lower() for domain in own_domains or ()]
        return [domain for domain in domains if domain]

    @staticmethod
    def _is_own_sender(sender_line: str, domains: list) -> bool:
        """
        Whether a sender line belongs to the receiving side: ``domains`` is not empty and the line's email address is
        in one of them or a subdomain of one, or the line carries no email address at all.

        :param sender_line: The line naming the sender of a quoted message.
        :param domains: The receiving side's domains, as returned by ``_normalise_own_domains``.
        :return: True if the sender is treated as the receiving side's.
        """
        if not domains:
            return False

        address = EmailReplyParser.EMAIL_ADDRESS_REGEX.search(sender_line)
        if not address:
            return True
        sender_domain = address.group(0).rsplit('@', 1)[-1].lower()
        return any(sender_domain == domain or sender_domain.endswith('.' + domain) for domain in domains)

    @staticmethod
    def _has_content(reply: str) -> bool:
        """
        Whether a parsed reply holds anything besides blank, divider and "Sent from ..." lines.

        :param reply: The parsed reply.
        :return: True if the reply has content.
        """
        return any(line.strip() and not EmailReplyParser._is_divider_or_device_line(line.strip())
                   for line in reply.split('\n'))

    @staticmethod
    def _is_divider_or_device_line(line: str) -> bool:
        """
        Whether a stripped line is a divider (e.g. ``____``, ``-----Original Message-----``) or "Sent from ..." line.

        :param line: The stripped line to check.
        :return: True if the line is a divider or device line.
        """
        return EmailMessage.SENT_FROM_DEVICE_REGEX.match(unidecode.unidecode(line)) is not None


class EmailMessage(object):
    """ An email message represents a parsed email body.
        The regexes cover English, Italian, Swedish, Finnish, Danish, German, Portuguese, Polish, French to date.
    """
    SENT_FROM_DEVICE_REGEX = re.compile(
        r"(^--|^__|^\* \* \*|^\*\*[\s.]+\*\*$)"
        r"|(^Sent from .{,50}$)"  # English
        r"|(^Sent using the mobile mail app)"  # English
        r"|(^Get Outlook for .{,50}$)"  # English
        r"|(^Sendt fra .{,50}$)"  # Danish
        r"|(^Verstuurd vanaf.{,50}$)"  # Dutch
        r"|(^Verzonden vanuit .{,50}$)"  # Dutch
        r"|(^Hanki .{,50}$)"  # Finnish
        r"|(^Lahetetty .{,50}$)"  # Finnish
        r"|(^Envoye de .{,50}$)"  # French
        r"|(^Envoye depuis .{,50}$)"  # French
        r"|(^Envoye a partir .{,50}$)"  # French
        r"|(^Gesendet mit.{,50}$)"  # German
        r"|(^Gesendet von.{,50}$)"  # German
        r"|(^Estale apo .{,50}$)"  # Greek
        r"|(.{0,50} kuldve$)"  # Hungarian
        r"|(^Inviato da .{,50}$)"  # Italian
        r"|(^Inviato dal .{,50}$)"  # Italian
        r"|(^Wyslane z .{,50}$)"  # Polish
        r"|(^Wysłane z .{,50}$)"  # Polish
        r"|(^Enviado de .{,50}$)"  # Portuguese
        r"|(^Enviado desde .{,50}$)"  # Portuguese
        r"|(^Enviado do .{,50}$)"  # Portuguese
        r"|(^Enviado a partir .{,50}$)"  # Portuguese
        r"|(^Obter o Outlook .{,50}$)"  # Portuguese
        r"|(^Obtener Outlook .{,50}$)"  # Spanish
        r"|(^Trimis de pe .{,50}$)"  # Romanian
        r"|(^Skickat från .{,50}$)"  # Swedish
        r"|(^Skickat fran .{,50}$)"  # Swedish
        r"|(^Στάλθηκε από .{,50}$)"  # Greek
        r"|(احصل على .{,50}$)"  # Arabic
        r"|(\u202B?أُرسلت من الـ .{,50}$)"  # Arabic
        r"|(\u200F?\u202B?من الـ iPhone .{,50}$)", # Arabic
        flags=re.MULTILINE
    )

    QUOTE_HDR_REGEX = re.compile(
        r"On.*wrote(.*?):$"  # English
        r"|Il.*\bha\b(.*?)$"  # Italian - in italian the phrase is "ha scritto" but sometimes "scritto" is put on a new line so we won't put the colon at the end
        r"|mån.*skrev(.*?):$"  # Swedish
        r"|man.*skrev(.*?):$"  # Swedish
        r"|tis.*skrev(.*?):$"  # Norwegian
        r"|tors.*skrev(.*?):$"  # Norwegian
        r"|ons.*skrev(.*?):$"  # Norwegian
        r"|Am.*schrieb(.*?):$"  # German
        r"|Von.*gesendet(.*?)"  # German
        r"|.*[>|;] schrieb.*[0-9]{2}:[0-9]{2}:"  # German
        r"|Ende der Kundennachricht"  # German
        r"|ma.*kirjoitti(.*?):$"  # Finnish
        r"|ti.*kirjoitti(.*?):$"  # Finnish
        r"|pe.*kirjoitti(.*?):$"  # Finnish
        r"|ke.*kirjoitti(.*?):$"  # Finnish
        r"|Den.*skrev(.*?):$"  # Danish
        r"|fre.*skrev(.*?):$"  # Danish
        r"|tir.*skrev(.*?):$"  # Danish
        r"|Op.*schreef(.*?):$"  # Dutch
        r"|Op.*geschreven(.*?):$"  # Dutch
        r"|No dia.*escreveu(.*?):$"  # Portuguese
        r"|A.*escreveu(.*?):$"  # Portuguese
        r"|[A-Z].*[>|;] escreveu(.*?):$"  # Portuguese
        r"|[A-Z].*[0-9]{2}:[0-9]{2}.*@.*escreveu:$"  # Portuguese
        r"|Le.*ecrit(.*?):$"  # French
        r"|El.*escribio(.*?):$"  # Spanish
        r"|El.*escribió(.*?):$"  # Spanish
        r"|En.*escribio(.*?):$"  # Spanish
        r"|En.*escribió(.*?):$"  # Spanish
        r"|Dna.*napisal\(a\)(.*?):$"  # Slovak
        r"|po.*napisal\(a\)(.*?):$"  # Slovak
        r"|Dnia.*napisal\(a\)(.*?):$"  # Polish
        r"|Dnia.*napisał\(a\)(.*?):$"  # Polish
        r"|Στις.*έγραψε(.*?):$"  # Greek
        r"|.*[0-9]{2}:[0-9]{2}.*a scris(.*?):$"  # Romanian
        r"|Dne.*napsal(.*?):$"  # Czech
        r"|\u202B?في.*كتب/كتبت(.*?):"  # Arabic
        r"|\u202B?في.*(كتب|كتبت)(.*?):$"  # Arabic
        r"|\u202B?بتاريخ.*(كتب|كتبت)(.*?):$"  # Arabic
    )

    QUOTED_REGEX = re.compile(r"(>+)")
    HEADER_REGEX = re.compile(
        r"(^(\*+)?.|^(\*)?)(From|Sent|To|Subject"  # English - Need ^(\*+)?. to catch any number of asterisks before
                                                   # the matching word and ^(\*)? to catch for no asterisks 
        r"|Da|A|Data|Oggetto|Inviato"  # Italian
        r"|Från|Datum|Till|Ämne|Skickat"  # Swedish
        r"|Fran|Datum|Till|Amne|Skickat"  # Swedish
        r"|Von|Gesendet|An|Betreff|Datum"  # German
        r"|Lähettäjä|Päiväys|Vastaanottaja|Aihe|Lähetetty"  # Finnish
        r"|Lahettaja|Paivays|Vastaanottaja|Aihe|Lähetetty"  # Finnish
        r"|Fra|Sendt|Til|Emne|Dato"  # Danish
        r"|Obtenir|Telechargez|Envoye|De"  # French
        r"|Από το|Αποστολή|Προς|Θέμα"  # Greek
        r"|De la|Început|La|Subiect"  # Romanian
        r"|De|Enviado|A|Asunto"  # Spanish
        r"|من|تم الإرسال|إلى|الموضوع"  # Arabic
        r"|De|Enviado|Para|Assunto|Data):\*?"  # Portuguese
    )
    # Strict bold-markdown header form produced by Outlook/Zendesk (e.g. ``**Von:**``,
    # ``**Betreff:**``). Requires the opening ``**`` immediately followed by a keyword and a
    # colon, so a stray bold line such as ``**To** the team`` does not match.
    BOLD_HEADER_REGEX = re.compile(r"^\*\*[^*]+:")
    _MULTI_QUOTE_HDR_REGEX = (
        r"(On (.{,120})\n?(.{,50})?wrote(\s+)?:"  # English
        r"|Il (.{,120})\n?(.{,50})?ha(\s+)?:"  # Italian
        r"|Il (.{,120})\n?(.{,50})?ha(\s+)?scritto:"  # Italian
        r"|mån (.{,120})\n?(.{,50})?skrev(\s+)?:"  # Swedish
        r"|man (.{,120})\n?(.{,50})?skrev(\s+):"  # Swedish
        r"|tis (.{,120})\n?(.{,50})?skrev(\s+):"  # Norwegian
        r"|tors (.{,120})\n?(.{,50})?skrev(\s+):"  # Norwegian
        r"|ons (.{,120})\n?(.{,50})?skrev(\s+):"  # Norwegian
        r"|Am (.{,120})\n?(.{,50})?schrieb(\s+)?::"  # German
        r"|Am (.{,120})\bschrieb\b(.{,50})?(\s+)?(:)?"  # German
        r"|(.{,50})?\bschrieb\b(.{,120})(\s+)?(:)?"  # German
        r"|(-(-*)?\s?(Ursprüngliche|Original).?(Nachricht|Message)\s?(-*)?-)" #German/English
        r"|-(-*)?\s?Forwarded.?Message\s?(-*)?-" #German/English
        r"|ma (.{,120})\n?(.{,50})?kirjoitti(\s+)?:"  # Finnish
        r"|ti (.{,120})\n?(.{,50})?kirjoitti(\s+)?:"  # Finnish
        r"|pe (.{,120})\n?(.{,50})?kirjoitti(\s+)?:"  # Finnish
        r"|ke (.{,120})\n?(.{,50})?kirjoitti(\s+)?:"  # Finnish
        r"|fre (.{,120})\n?(.{,50})?skrev(\s+)?:"  # Danish
        r"|Den (.{,120})\n?(.{,50})?skrev(\s+)?:"  # Danish
        r"|tir (.{,120})\n?(.{,50})?skrev(\s+)?:"  # Danish
        r"|Op (.{,120})\n?(.{,50})?schreef(\s+)?:"  # Dutch
        r"|Op (.{,120})\n?(.{,50})?geschreven(\s+)?:"  # Dutch
        r"|A (.{,120})\n?(.{,50})?escreveu(\s+)?:"  # Portuguese
        r"|No dia (.{,120})\n?(.{,50})?escreveu(\s+)?:"  # Portuguese
        r"|El (.{,120})\n?(.{,50})?escribio(\s+)?:"  # Spanish
        r"|El (.{,120})\n?(.{,50})?escribió(\s+)?:"  # Spanish
        r"|Le (.{,120})\n?(.{,50})?ecrit(\s+)?:?"  # French
        r"|Le (.{,120})\n?(.{,50})?écrit(\s+)?:?"  # French
        r"|Dna (.{,120})\n?(.{,50})?napisala\(a\)(\s+)?:"  # Slovak
        r"|po (.{,120})\n?(.{,50})?napisal\(a\)(\s+)?:"  # Slovak
        r"|Dnia (.{,120})\n?(.{,50})?napisal\(a\)(\s+)?:" # Polish
        r"|Dnia (.{,120})\n?(.{,50})?napisał\(a\)(\s+)?:" # Polish
        r"|W dniu (.{,120})\n?(.{,50})?napisal(\s+)?:" # Polish
        r"|W dniu (.{,120})\n?(.{,50})?napisał(\s+)?:" # Polish
        r"|Wiadomość napisana (.{,120})\n?(.{,50})?o godz" # Polish
        r"|Wiadomosc napisana (.{,120})\n?(.{,50})?o godz" # Polish
        r"|Temat: (.{,120})\n?(.{,50})?Adresat:" # Polish
        r"|Στις (.{,120})\n?(.{,50})?έγραψε(\s+)?:"  # Greek
        r"|\u202B?في (.{,120})\n?(.{,50})?كتب/كتبت(\s+)?:" # Arabic
        r"|\u202B?في (.{,120})\n?(.{,50})?(كتب|كتبت)(\s+)?:" # Arabic
        r"|\u202B?بتاريخ (.{,120})\n?(.{,50})?(كتب|كتبت)(\s+)?:" # Arabic
        r")"
    )
    MULTI_QUOTE_HDR_REGEX = re.compile(_MULTI_QUOTE_HDR_REGEX,flags=re.IGNORECASE)

    EMAIL_SIGNOFF_REGEX = re.compile(
        r"((regards|kind regards|warm regards|best regards|best wishes|all the best|mit besten grüßen|mit besten gruben|cheers|"
        r"cordialement|très cordialement|bien cordialement|bien a vous|merci d'avance|d'avance merci|"
        r"Vielen Dank und LG|Herzliche Grusse|grussen\s?|grusse\s?|liebe Grusse\s?|"
        r"vielen dank im voraus|Mit freundlichen grussen|Mit freundlichen Grüssen|"
        r"Mit freundlichen grüßen|Freundliche Grüße|Freundliche Grüsse|Freundliche Grusse|"
        r"saluti|Cordiali saluti|Distinti saluti|buona giornata|cordialmente|"
        r"o zi buna|o zi buna va urez|cu respect|cu stima|cu bine|toate cele bune|"
        r"saludos cordiales|atentamente|un saludo)(.{0,20})(,|\n|\Z))|(sincerely.{0,5}(,|\n|\Z))|"
        r"((thank you|thanks!?|thank you in advance|thanks in advance|merci|danke|Vielen Dank|"
        r"grazie|grazie mille|multumesc\s?|multumesc anticipat|multumesc frumos|gracias|muchos gracias)(,?!?\n))|"
        r"(Pozdrawiam.?|Z powazaniem|z pozdrowieniami)",
        # No Email signature for arabic because they are uncommon and not standard practise
        flags=re.IGNORECASE
    )

    EMAIL_HEADER_WARNINGS = [
        "CAUTION:This message is from an EXTERNAL SENDER - be CAUTIOUS, Do NOT Click any links or Open any attachments if you were not expecting them."
    ]

    def __init__(self, text):
        self.fragments = []
        self.fragment = None
        self.text = text.replace('\r\n', '\n')
        self.found_visible = False

    def _strip_leading_header_block(self) -> None:
        """
        Handle "bottom-posting" emails where the quoted-message headers (e.g. ``**Von:**``,
        ``**Gesendet:**``, ``**An:**``, ``**Betreff:**`` in German Outlook) appear at the very
        start of the body, with the customer's actual reply placed *below* them.

        The method walks forward over the contiguous block of header lines (ignoring the blank
        lines that separate them) and, when the block is unambiguously a quoted-header block,
        sets ``self.text`` to the content that follows so the reverse-scan algorithm sees only
        the reply rather than marking it hidden because headers appear "before" it in reverse.

        To avoid eating a genuine reply whose first line merely starts with a word that
        ``HEADER_REGEX`` also matches (e.g. "A", "De", "To"), the block is only stripped when it
        is unambiguous: either it contains **two or more** stacked header lines, or its first
        header line uses the bold-markdown Outlook form (``**Von:** ...``).

        If the body does **not** start with such a block the method is a no-op.
        """
        lines = self.text.split('\n')
        first_index = next((index for index, line in enumerate(lines) if line.strip()), None)
        if first_index is None or not self.HEADER_REGEX.match(lines[first_index].strip()):
            return

        header_count = 0
        content_start = first_index
        for index in range(first_index, len(lines)):
            stripped = lines[index].strip()
            if not stripped:
                continue  # Blank line separating header lines — keep scanning.
            if self.HEADER_REGEX.match(stripped):
                header_count += 1
                content_start = index + 1
            else:
                break  # First non-header, non-blank line — the reply starts here.

        first_header_is_bold = self.BOLD_HEADER_REGEX.match(lines[first_index].strip()) is not None
        if header_count < 2 and not first_header_is_bold:
            return

        if 0 < content_start < len(lines):
            self.text = '\n'.join(lines[content_start:])

    def read(self):
        """ Creates new fragment for each line
            and labels as a signature, quote, or hidden.

            Returns EmailMessage instance
        """

        self.found_visible = False

        # Strip a leading quoted-header block produced by bottom-posting email clients
        # (e.g. German Outlook where Von/Gesendet/An/Betreff appear at the top and the
        # customer's reply follows below).
        self._strip_leading_header_block()

        is_multi_quote_header = self.MULTI_QUOTE_HDR_REGEX.search(self.text.strip())
        if is_multi_quote_header:
            self.text = self.text.strip()[:is_multi_quote_header.start()]

        # Fix any outlook style replies, with the reply immediately above the signature boundary line
        #   See email_2_2.txt for an example
        self.text = re.sub('([^\n])(?=\n ?[_-]{7,})', '\\1\n', self.text, re.MULTILINE)

        self.lines = self.text.split('\n')
        self.lines.reverse()

        for line in self.lines:
            self._scan_line(line)

        self._finish_fragment()

        self.fragments.reverse()

        return self

    @property
    def reply(self):
        """ Captures reply message within email
        """
        reply = []
        for f in self.fragments:
            if not (f.hidden or f.quoted):
                reply.append(f.content)
        return '\n'.join(reply)

    def _scan_line(self, line):
        """ Reviews each line in email message and determines fragment type
            line - a row of text from an email message
        """
        is_quote_header = self.QUOTE_HDR_REGEX.match(line.strip()) is not None
        is_quoted = self.QUOTED_REGEX.match(line) is not None
        is_header = is_quote_header or self.HEADER_REGEX.match(line) is not None

        if self.fragment and len(line.strip()) == 0:
            if self.SENT_FROM_DEVICE_REGEX.match(self.fragment.lines[-1].strip()):
                self.fragment.signature = True
                self._finish_fragment()

        if self.fragment \
                and ((self.fragment.headers == is_header and self.fragment.quoted == is_quoted) or
                     (self.fragment.quoted and (is_quote_header or len(line.strip()) == 0))):

            self.fragment.lines.append(line)
        else:
            self._finish_fragment()
            self.fragment = Fragment(is_quoted, line, headers=is_header)

    def quote_header(self, line):
        """ Determines whether line is part of a quoted area

            line - a row of the email message

            Returns True or False
        """
        return self.QUOTE_HDR_REGEX.match(line[::-1]) is not None

    def _finish_fragment(self):
        """ Creates fragment
        """

        if self.fragment:
            self.fragment.finish()
            if self.fragment.headers:
                # Regardless of what's been seen to this point, if we encounter a headers fragment,
                # all the previous fragments should be marked hidden and found_visible set to False.
                self.found_visible = False
                for f in self.fragments:
                    f.hidden = True
            if not self.found_visible:
                if self.fragment.quoted \
                        or self.fragment.headers \
                        or self.fragment.signature \
                        or (len(self.fragment.content.strip()) == 0):

                    self.fragment.hidden = True
                else:
                    self.found_visible = True
            self.fragments.append(self.fragment)
        self.fragment = None

    @staticmethod
    def clean_email_content(body, include: Optional[bool], word_limit: Optional[int]):
        """
        Determines if a signature can be found and if so, whether to end the email before or after the signature.
        """
        # Make unidecode copy of body to check against SENT_FROM_DEVICE_REGEX and EMAIL_SIGNOFF_REGEX
        body_clean = EmailMessage.unidecode_with_exceptions(body, UNIDECODE_EXCEPTIONS)

        # Find sign-off or sent from device match for unidecode copy
        signoff_matches = list(EmailMessage.EMAIL_SIGNOFF_REGEX.finditer(body_clean))

        # Note we need to ignore the sent from if it is on the first line of the message
        end_of_first_line_index = body_clean.find("\n")

        # If the signoff match is in the first line of an email, it is likely a mistake (e.g. "Dear Mr. George Best,")
        signoff_matches = [match for match in signoff_matches if match.start() > end_of_first_line_index]


        sent_from_device_matches = []
        if end_of_first_line_index != -1:
            sent_from_device_matches = EmailMessage.SENT_FROM_DEVICE_REGEX.finditer(body_clean)
            sent_from_device_matches = [
                match for match in sent_from_device_matches if match.start() > end_of_first_line_index
            ]

        if include is True:
            # Keep the sign-off
            body = EmailMessage.keep_signoff(body, signoff_matches, sent_from_device_matches, word_limit)

        else:
            # Remove the sign-off
            body = EmailMessage.remove_signoff(body, signoff_matches, sent_from_device_matches, word_limit)

        # Split the body into lines and remove any "Sent from iPhone" lines
        # Use the unidecode copy to check for matches but remove lines from original body
        body = body.strip()
        body_lines = body.split('\n')
        body_lines_unidecode = unidecode.unidecode(body).split('\n')

        # Check if the first line matches and remove
        if EmailMessage.SENT_FROM_DEVICE_REGEX.match(body_lines_unidecode[0]):
            body_lines = body_lines[1:]

        # Check if the final line matches, remove, and re-join lines
        #if SIG_REGEX.match(body_lines_unidecode[-1]):
        if EmailMessage.SENT_FROM_DEVICE_REGEX.match(body_lines_unidecode[-1]):
            body = '\n'.join(body_lines[:-1])
        else:
            body = '\n'.join(body_lines)

        # Finally remove any warning headers from the email
        body = EmailMessage.remove_substrings_from_text(body, EmailMessage.EMAIL_HEADER_WARNINGS)

        return body

    @staticmethod
    def keep_signoff(
            body: str,
            signoff_matches: List[re.Match],
            sent_from_device_matches: List[re.Match],
            word_limit: Optional[int] = None
    ):
        """
        Find where the signature ends and cut-off the email at that point.
        """

        # first handle any sent from iphone stuff
        if len(sent_from_device_matches) > 0:
            sent_from_device_matches_start = [
                match.start() for match in sent_from_device_matches
            ]
            body = body[:sent_from_device_matches_start[0]]

        # Find where sign-off ends
        signoff_matches_end_positions = [
            signoff_match.end() for signoff_match in signoff_matches
        ]

        if len(signoff_matches_end_positions) > 0 and signoff_matches_end_positions[0] < len(body):
            # If a sign-off was found, check for a signature
            end_of_email = body[signoff_matches_end_positions[0]:]

            signature_matches = re.finditer(
                r"((\w+)[\n.])+|\Z",
                end_of_email,
                flags=re.IGNORECASE
            )

            signature_matches_end_positions = [
                signature_match.end() for signature_match in signature_matches
            ]

            if len(signature_matches_end_positions) > 0:
                # If a signature exists, add the two end positions to get the email cut-off point
                email_cutoff = signoff_matches_end_positions[0] + signature_matches_end_positions[0]
                body = body[:email_cutoff]

            else:
                # If no signature found, cut email off after the sign-off
                body = body[:signoff_matches_end_positions[0]]

        else:
            # If no sign-off found, cut-off after word limit
            body = EmailMessage.word_limit_cut_off(body, word_limit)

        return body

    @staticmethod
    def remove_signoff(
            body: str,
            signoff_matches: List[re.Match],
            sent_from_device_matches: List[re.Match],
            word_limit: Optional[int] = None
    ):
        """
        Find where the sign-off starts and cut-off the email at that point.
        """
        # first handle any sent from iphone stuff
        if len(sent_from_device_matches) > 0:
            sent_from_device_matches_start = [
                match.start() for match in sent_from_device_matches
            ]
            body = body[:sent_from_device_matches_start[0]]

        # Find where signature starts
        signoff_matches_start_positions = [
            signoff_match.start() for signoff_match in signoff_matches
        ]

        if len(signoff_matches_start_positions) > 0 and signoff_matches_start_positions[0] < len(body):
            # If a sign-off was found, cut-off email at starting position
            body = body[:signoff_matches_start_positions[0]]

        else:
            # If no sign-off found, cut-off at word limit
            EmailMessage.word_limit_cut_off(body, word_limit)

        return body

    @staticmethod
    def word_limit_cut_off(body, word_limit):
        """
        Cut-off email at word limit.
        """
        if word_limit is not None:
            # if we can't find the sign-off, let's just take the first 100 words
            email_body_list = body.replace("\n", " \n").split(" ")
            newlines_offset = len([word for word in email_body_list if word == " \n"])
            body = " ".join(email_body_list[:word_limit + newlines_offset]).replace(" \n", "\n")

        return body

    @staticmethod
    def remove_substrings_from_text(body: str, substrings: List[str]) -> str:
        """
        Given an email body and a list of substrings to remove (e.g. external email warning), loop through them and
        replace
        """
        for substring in substrings:
            body = re.sub(substring, "", body)

        return body.strip()

    @staticmethod
    def unidecode_with_exceptions(text: str, exceptions: Dict):
        """
        Handles cases where some characters such as € gets replace with EUR and this messes up regex match positions
        """
        # Replace exceptions with placeholders
        for char, placeholder in exceptions.items():
            text = text.replace(char, placeholder)

        # Apply unidecode
        decoded_text = unidecode.unidecode(text)

        # Replace placeholders back with original characters
        for char, placeholder in exceptions.items():
            decoded_text = decoded_text.replace(placeholder, char)

        return decoded_text


class Fragment(object):
    """ A Fragment is a part of
        an Email Message, labeling each part.
    """

    def __init__(self, quoted, first_line, headers=False):
        self.signature = False
        self.headers = headers
        self.hidden = False
        self.quoted = quoted
        self._content = None
        self.lines = [first_line]

    def finish(self):
        """ Creates block of content with lines
            belonging to fragment.
        """
        self.lines.reverse()
        self._content = '\n'.join(self.lines)
        self.lines = None

    @property
    def content(self):
        return self._content.strip()

