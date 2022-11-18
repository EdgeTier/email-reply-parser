"""
    email_reply_parser is a python library port of GitHub's Email Reply Parser.

    For more information, visit https://github.com/zapier/email-reply-parser
"""

import re
from typing import Optional
import unidecode


class EmailReplyParser(object):
    """ Represents an email message that is parsed.
    """

    @staticmethod
    def read(text):
        """ Factory method that splits email into list of fragments

            text - A string email body

            Returns an EmailMessage instance
        """
        return EmailMessage(text).read()

    @staticmethod
    def parse_reply(text):
        """ Provides the reply portion of email.

            text - A string email body

            Returns reply body message
        """
        return EmailReplyParser.read(text).reply

    @staticmethod
    def cut_off_at_signature(body: str, include: Optional[bool] = True, word_limit: Optional[int] = 100):
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
        """
        parsed_email = EmailReplyParser.parse_reply(body)
        cleaned_email = EmailMessage.clean_email_content(parsed_email, include, word_limit)
        return cleaned_email.strip()


class EmailMessage(object):
    """ An email message represents a parsed email body.
        The regexes cover English, Italian, Swedish, Finnish, Danish, German, Portuguese, Polish, French to date.
    """
    SIG_REGEX = re.compile(
        r"(--|__|-\w)|(^Sent from .*(?:\r?\n(?!\r?\n).*)*)"  # English
        r"|(^Inviato da .*(?:\r?\n(?!\r?\n).*)*)"  # Italian
        r"|(^Inviato dal .*(?:\r?\n(?!\r?\n).*)*)"  # Italian
        r"|(^Skickat från .*(?:\r?\n(?!\r?\n).*)*)"  # Swedish
        r"|(^Skickat fran .*(?:\r?\n(?!\r?\n).*)*)"  # Swedish
        r"|(^Gesendet mit.*(?:\r?\n(?!\r?\n).*)*)"  # German
        r"|(^Hanki .*(?:\r?\n(?!\r?\n).*)*)"  # Finnish
        r"|(^Lähetetty .*(?:\r?\n(?!\r?\n).*)*)"  # Finnish
        r"|(^Lahetetty .*(?:\r?\n(?!\r?\n).*)*)"  # Finnish
        r"|(^Sendt fra .*(?:\r?\n(?!\r?\n).*)*)"  # Danish
        r"|(^Enviado de .*(?:\r?\n(?!\r?\n).*)*)"  # Portuguese
        r"|(^Enviado desde .*(?:\r?\n(?!\r?\n).*)*)"  # Portuguese
        r"|(^Verstuurd vanaf .*(?:\r?\n(?!\r?\n).*)*)"  # Dutch
        r"|(^Envoye .*(?:\r?\n(?!\r?\n).*)*)"  # French
    )

    QUOTE_HDR_REGEX = re.compile(
        r"On.*wrote(.*?):$"  # English
        r"|Il.*ha(.*?)$"  # Italian - in italian the phrase is "ha scritto" but sometimes "scritto" is put on a new line so we won't put the colon at the end
        r"|mån.*skrev(.*?):$"  # Swedish
        r"|man.*skrev(.*?):$"  # Swedish
        r"|tis.*skrev(.*?):$"  # Norwegian
        r"|tors.*skrev(.*?):$"  # Norwegian
        r"|ons.*skrev(.*?):$"  # Norwegian
        r"|Am.*schrieb(.*?):$"  # German
        r"|Von.*gesendet(.*?)"  # German
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
        r"|Le.*ecrit(.*?):$"  # French
        r"|El.*escribio(.*?):$"  # Spanish
        r"|Dna.*napisal\(a\)(.*?):$"  # Slovak
        r"|po.*napisal\(a\)(.*?):$"  # Slovak
        r"|Dnia.*napisal\(a\)(.*?):$"  # Polish
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
        r"|De|Enviado|Para|Assunto|Data):\*?"  # Portuguese
    )
    _MULTI_QUOTE_HDR_REGEX = (
        r"(?!On.*On\s.+?wrote:)"  # English
        r"(On\s(.+?)wrote:"  # English
        r"|Il\s(.+?)ha(.*?)"  # Italian
        r"|mån\s(.+?)skrev(.*?):"  # Swedish
        r"|man\s(.+?)skrev(.*?):"  # Swedish
        r"|tis\s(.+?)skrev(.*?):"  # Norwegian
        r"|tors\s(.+?)skrev(.*?):"  # Norwegian
        r"|ons\s(.+?)skrev(.*?):"  # Norwegian
        r"|Am\s(.+?)schrieb(.*?):"  # German
        r"|ma\s(.+?)kirjoitti(.*?):"  # Finnish
        r"|ti\s(.+?)kirjoitti(.*?):"  # Finnish
        r"|pe\s(.+?)kirjoitti(.*?):"  # Finnish
        r"|ke\s(.+?)kirjoitti(.*?):"  # Finnish
        r"|fre\s(.+?)skrev(.*?):"  # Danish
        r"|Den\s(.+?)skrev(.*?):"  # Danish
        r"|tir\s(.+?)skrev(.*?):"  # Danish
        r"|Op\s(.+?)schreef(.*?):"  # Dutch
        r"|Op\s(.+?)geschreven(.*?):"  # Dutch
        r"|A\s(.+?)escreveu(.*?):"  # Portuguese
        r"|No dia\s(.+?)escreveu(.*?):"  # Portuguese
        r"|El\s(.+?)escribio(.*?):"  # Spanish
        r"|Le\s(.+?)ecrit(.*?):"  # French
        r"|Dna\s(.+?)napisala\(a\)(.*?):"  # Slovak
        r"|po\s(.+?)napisal\(a\)(.*?):"  # Slovak
        r"|Dnia\s(.+?)napisal\(a\)(.*?):)"  # Polish
    )
    MULTI_QUOTE_HDR_REGEX = re.compile(_MULTI_QUOTE_HDR_REGEX, re.DOTALL | re.MULTILINE)
    MULTI_QUOTE_HDR_REGEX_MULTILINE = re.compile(_MULTI_QUOTE_HDR_REGEX, re.DOTALL)

    EMAIL_SIGNOFF_REGEX = (
        r"((regards|kind regards|warm regards|best regards|best wishes|sincerely|best|cheers|"
        r"cordialement|très cordialement|bien cordialement|bien a vous|merci d'avance|d'avance merci|"
        r"Vielen Dank|Vielen Dank und LG|Herzliche Grusse|grussen\s?|grusse\s?|liebe Grusse\s?|"
        r"vielen dank im voraus|Mit freundlichen grussen|"
        r"saluti|Cordiali saluti|Distinti saluti|buona giornata|cordialmente|"
        r"o zi buna|o zi buna va urez|cu respect|cu stima|cu bine|toate cele bune|"
        r"saludos cordiales|atentamente|un saludo)(.?)(,|\n))|"
        r"((thank you|thanks!?|thank you in advance|thanks in advance|merci|danke|"
        r"grazie|grazie mille|multumesc\s?|multumesc anticipat|multumesc frumos|gracias|muchos gracias)(,?!?\n))"
    )

    def __init__(self, text):
        self.fragments = []
        self.fragment = None
        self.text = text.replace('\r\n', '\n')
        self.found_visible = False

    def read(self):
        """ Creates new fragment for each line
            and labels as a signature, quote, or hidden.

            Returns EmailMessage instance
        """

        self.found_visible = False

        is_multi_quote_header = self.MULTI_QUOTE_HDR_REGEX_MULTILINE.search(self.text)
        if is_multi_quote_header:
            self.text = self.MULTI_QUOTE_HDR_REGEX.sub(is_multi_quote_header.groups()[0].replace('\n', ''), self.text)

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
        is_quote_header = self.QUOTE_HDR_REGEX.match(line) is not None
        is_quoted = self.QUOTED_REGEX.match(line) is not None
        is_header = is_quote_header or self.HEADER_REGEX.match(line) is not None

        if self.fragment and len(line.strip()) == 0:
            if self.SIG_REGEX.match(self.fragment.lines[-1].strip()):
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
    def clean_email_content(body, include: Optional[bool], word_limit):
        """
        Determines if a signature can be found and if so, whether to end the email before or after the signature.
        """
        body = unidecode.unidecode(body)
        email_signoff_regex = EmailMessage.EMAIL_SIGNOFF_REGEX

        # Find sign-off
        signoff_matches = re.finditer(
            email_signoff_regex,
            body,
            flags=re.IGNORECASE,
        )

        if include is True:
            # Keep the sign-off
            body = EmailMessage.keep_signoff(body, signoff_matches, word_limit)

        else:
            # Remove the sign-off
            body = EmailMessage.remove_signoff(body, signoff_matches, word_limit)

        return body

    @staticmethod
    def keep_signoff(body, signoff_matches, word_limit: Optional[int] = 100):
        """
        Find where the signature ends and cut-off the email at that point.
        """
        # Find where sign-off ends
        signoff_matches_end_positions = [
            signoff_match.end() for signoff_match in signoff_matches
        ]

        if len(signoff_matches_end_positions) > 0:
            # If a sign-off was found, check for a signature
            end_of_email = body[signoff_matches_end_positions[0]:]

            signature_matches = re.finditer(
                # TODO: Check if ((\w+)[\n.])+|\Z works instead (\Z to get the absolute end of a string)
                r"((\w+)[\n.])+|\Z",
                # r"((\w+)[\n.])+",  # returns the first line after the sign-off
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
    def remove_signoff(body, signoff_matches, word_limit: Optional[int] = 100):
        """
        Find where the sign-off starts and cut-off the email at that point.
        """
        # Find where signature starts
        signoff_matches_start_positions = [
            signoff_match.start() for signoff_match in signoff_matches
        ]

        if len(signoff_matches_start_positions) > 0:
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
            email_body_list = body.split()
            body = " ".join(email_body_list[:word_limit])

        return body


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
