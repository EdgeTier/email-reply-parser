import os
import sys
import unittest
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from email_reply_parser import EmailMessage, EmailReplyParser


class EmailMessageTest(unittest.TestCase):
    def test_simple_body(self):
        message = self.get_email('email_1_1')

        self.assertEqual(2, len(message.fragments))
        self.assertEqual(
            [False, True],
            [f.signature for f in message.fragments]
        )
        self.assertEqual(
            [False, True],
            [f.hidden for f in message.fragments]
        )
        self.assertTrue("folks" in message.fragments[0].content)
        self.assertTrue("riak-users" in message.fragments[1].content)

    def test_multiline_reply_headers(self):
        message = self.get_email('email_1_6')
        print(message)
        self.assertTrue('I get' in message.fragments[0].content)
        self.assertTrue('Sent' in message.fragments[1].content)

    def test_complex_body_with_one_fragment(self):
        message = self.get_email('email_1_5')

        self.assertEqual(1, len(message.fragments))

    def test_verify_reads_signature_correct(self):
        message = self.get_email('correct_sig')
        self.assertEqual(2, len(message.fragments))

        self.assertEqual(
            [False, False],
            [f.quoted for f in message.fragments]
        )

        self.assertEqual(
            [False, True],
            [f.signature for f in message.fragments]
        )

        self.assertEqual(
            [False, True],
            [f.hidden for f in message.fragments]
        )

        self.assertTrue('--' in message.fragments[1].content)

    def test_deals_with_windows_line_endings(self):
        msg = self.get_email('email_1_7')
        self.assertTrue(':+1:' in msg.fragments[0].content)

    def test_reply_from_gmail(self):
        with open('emails/email_gmail.txt') as f:
            self.assertEqual('This is a test for inbox replying to a github message.',
                             EmailReplyParser.parse_reply(f.read()))

    def test_parse_out_just_top_for_outlook_reply(self):
        with open('emails/email_2_1.txt') as f:
            self.assertEqual("Outlook with a reply", EmailReplyParser.parse_reply(f.read()))

    def test_parse_out_just_top_for_outlook_with_reply_directly_above_line(self):
        with open('emails/email_2_2.txt') as f:
            self.assertEqual("Outlook with a reply directly above line", EmailReplyParser.parse_reply(f.read()))

    def test_parse_out_just_top_for_outlook_with_unusual_headers_format(self):
        with open('emails/email_2_3.txt') as f:
            self.assertEqual(
                "Outlook with a reply above headers using unusual format",
                EmailReplyParser.parse_reply(f.read()))

    def test_sent_from_iphone(self):
        with open('emails/email_iPhone.txt') as email:
            self.assertTrue("Sent from my iPhone" not in EmailReplyParser.parse_reply(email.read()))

    def test_email_one_is_not_on(self):
        with open('emails/email_one_is_not_on.txt') as email:
            self.assertTrue(
                "On Oct 1, 2012, at 11:55 PM, Dave Tapley wrote:" not in EmailReplyParser.parse_reply(email.read()))

    def test_partial_quote_header(self):
        message = self.get_email('email_partial_quote_header')
        self.assertTrue("On your remote host you can run:" in message.reply)
        self.assertTrue("telnet 127.0.0.1 52698" in message.reply)
        self.assertTrue("This should connect to TextMate" in message.reply)

    def test_email_headers_no_delimiter(self):
        message = self.get_email('email_headers_no_delimiter')
        self.assertEqual(message.reply.strip(), 'And another reply!')

    def test_pathological_emails(self):
        t0 = time.time()
        message = self.get_email("pathological")
        self.assertTrue(time.time() - t0 < 1, "Took too long")

    def test_doesnt_remove_signature_delimiter_in_mid_line(self):
        message = self.get_email('email_sig_delimiter_in_middle_of_line')
        self.assertEqual(1, len(message.fragments))

    def get_email(self, name):
        """ Return EmailMessage instance
        """
        with open('emails/%s.txt' % name) as f:
            text = f.read()
        return EmailReplyParser.read(text)

    @staticmethod
    def get_email_text(name):
        """
        Return the raw text of a fixture email, unparsed.

        :param name: The fixture file name without its extension.
        :return: The file contents.
        """
        with open(f'emails/{name}.txt') as fixture:
            return fixture.read()

    def test_include_signature_true(self):
        # Test that the cut_off_at_signature function ends an email after the sign-off when include = True
        message_english = self.get_email('email_signature')
        message_german = self.get_email('email_german')
        message_french = self.get_email('email_french')
        message_arabic = self.get_email('email_arabic')

        body_english = EmailReplyParser.cut_off_at_signature(message_english.text, include=True, word_limit=100)
        body_german = EmailReplyParser.cut_off_at_signature(message_german.text, include=True, word_limit=100)
        body_french = EmailReplyParser.cut_off_at_signature(message_french.text, include=True, word_limit=100)
        body_arabic = EmailReplyParser.cut_off_at_signature(message_arabic.text, include=True, word_limit=100)

        assert body_english.endswith('Kind regards,\n\nPerrin Aybara')
        assert body_german.endswith('Mit freundlichen Grüßen,\n\nLukas')
        assert body_french.endswith('Bien à vous,\n\nNicolette Baudelaire')
        assert body_arabic.endswith('سيتم مراجعة الحساب مجددا بعد نشاطك القادم.')

    def test_include_signature_false(self):
        # Test that the cut_off_at_signature function ends an email before the sign-off when include = False
        message_english = self.get_email('email_signature')
        message_german = self.get_email('email_german')
        message_french = self.get_email('email_french')
        # No Email signature for arabic because they are uncommon and not standard practise

        body_english = EmailReplyParser.cut_off_at_signature(message_english.text, include=False, word_limit=100)
        body_german = EmailReplyParser.cut_off_at_signature(message_german.text, include=False, word_limit=100)
        body_french = EmailReplyParser.cut_off_at_signature(message_french.text, include=False, word_limit=100)

        assert body_english.endswith('email cut-off point.')
        assert body_german.endswith('November vornehmen.')
        assert body_french.endswith("s'il vous plaît?")

    def test_word_limit(self):
        # Test that a long email cuts off after the default or given word limit
        message = self.get_email('long_passage')
        body_default_limit = EmailReplyParser.cut_off_at_signature(message.text, word_limit=100)  # Default value
        body_short = EmailReplyParser.cut_off_at_signature(message.text, word_limit=10)  # Less than default
        body_long = EmailReplyParser.cut_off_at_signature(message.text, word_limit=500)  # More than default

        assert body_default_limit.endswith('"HERE IS ONE HUNDRED!"')
        assert body_short.endswith('TEN!')
        assert body_long.endswith('FIVE HUNDRED IS HERE!')

        message = self.get_email('test_word_limit')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True, word_limit=500)
        assert body.endswith('Cdt')

    def test_clean_email_portuguese(self):
        # Test Portuguese regex
        message = self.get_email('email_portuguese')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=False, word_limit=100)
        assert body.endswith("Cumprimentos\nPedro Mota")

    def test_clean_email_french(self):
        # Test Portuguese regex
        message = self.get_email('email_french_accent_sent_on')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=False, word_limit=100)
        assert body == "Bonjour, ca va bien!"

    def test_clean_email_arabic(self):
        # Test Arabic regex
        message = self.get_email('email_arabic_2')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=False, word_limit=100)
        assert body == "لدي ايداعات كثيره وخسائر كثيره واكرر طلبي"

    def test_clean_email_content_no_change(self):
        # Ensure that a short email with no reply and no signature doesn't change
        message = self.get_email('email_one_line')
        clean_content = EmailReplyParser.cut_off_at_signature(body=message.text, word_limit=1000)
        self.assertEqual(message.text, clean_content)

    def test_end_of_email(self):
        # Check that an email that continues after the sign-off (without being a header or reply) cuts off at signature
        message = self.get_email('email_continue_after_signoff')
        body = EmailReplyParser.cut_off_at_signature(message.text)
        assert body.endswith('Tom Bombadil')

    def test_keep_newlines_when_no_signoff(self):
        # Test that when there is no sign-off message detected at the end, the newlines/spacing are not changed
        message = self.get_email('email_no_signature')
        body = EmailReplyParser.cut_off_at_signature(message.text)
        assert body.endswith("Let's see if it works.\n\nK")

    def test_swiss_german_signoff(self):
        # Regression: "Freundliche Grüsse" (Swiss German) and its ASCII variant "Freundliche Grusse"
        # were absent from EMAIL_SIGNOFF_REGEX.  Also, the terminator group previously only matched
        # "," or "\n", so a sign-off at the very end of the string (no trailing newline) was not
        # stripped.  Both issues caused sign-off text and any quoted thread below it to leak into
        # the parsed reply as standalone messages.

        # 1. Sign-off at end-of-string — no trailing newline, no quoted thread.
        no_newline = self.get_email('swiss_german_signoff_no_trailing_newline')
        body_include = EmailReplyParser.cut_off_at_signature(no_newline.text, include=True, word_limit=None)
        body_exclude = EmailReplyParser.cut_off_at_signature(no_newline.text, include=False, word_limit=None)
        assert "Könnten Sie bitte" in body_include
        assert body_include.endswith("Freundliche Grüsse")
        assert body_exclude.strip() == "Könnten Sie bitte meine Einzahlung freigeben?"

        # 2. Sign-off followed by a quoted thread — the thread must be stripped.
        with_thread = self.get_email('swiss_german_signoff_with_quoted_thread')
        body_thread = EmailReplyParser.cut_off_at_signature(with_thread.text, include=True, word_limit=None)
        assert "schrieb am" not in body_thread, "Quoted thread header should be stripped"
        assert "Gerne bestätigen" not in body_thread, "Quoted body should be stripped"
        assert "Könnten Sie bitte" in body_thread

        # 3. parse_reply should also strip everything from the sign-off onwards.
        reply = EmailReplyParser.parse_reply(with_thread.text)
        assert "schrieb am" not in reply
        assert "Gerne bestätigen" not in reply

    def test_remove_SIG_REGEX_end(self):
        # Test that any "Sent from iPhone" messages are removed at the end of an email
        message_french = self.get_email('email_iphone_french')
        message_portuguese = self.get_email('email_iphone_portuguese')
        message_polish = self.get_email('email_iphone_polish')
        message_finnish = self.get_email('email_iphone_finnish')
        message_arabic = self.get_email('email_iphone_arabic')

        body_french = EmailReplyParser.cut_off_at_signature(message_french.text)
        body_portuguese = EmailReplyParser.cut_off_at_signature(message_portuguese.text)
        body_polish = EmailReplyParser.cut_off_at_signature(message_polish.text)
        body_finnish = EmailReplyParser.cut_off_at_signature(message_finnish.text)
        body_arabic = EmailReplyParser.cut_off_at_signature(message_arabic.text)

        assert body_french.endswith("Au revoir,\n\nKelsier")
        assert body_portuguese.endswith("Adeus,\n\nOtis")
        assert body_polish.endswith("Do widzenia,\n\nTriss")
        assert body_finnish.endswith("Hyvästi,\n\nTorin")
        assert body_arabic.endswith("أنا ماني فاهم أنتي تتكلمين عن شنو بضبط …؟")

    def test_remove_SIG_REGEX_start(self):
        # Test that any "Sent from iPhone" messages are removed at the beginning of an email
        message_english = self.get_email('email_iphone_start')
        message_german = self.get_email('email_iphone_start_german')
        body_english = EmailReplyParser.cut_off_at_signature(message_english.text)
        body_german = EmailReplyParser.cut_off_at_signature(message_german.text)
        assert body_english.startswith('Hi,\n\nCase where the')
        assert body_german.startswith('Hallo,\n\nFall, in dem das')


    def test_parse_response_headers(self):
        """
        Tests that we are parsing out email response headers correctly for multiple languages
        """
        message = self.get_email('email_polish_1')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body == "Ten tekst powinien pojawić się w treści"

        message = self.get_email('email_polish_2')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body == "Ten tekst powinien pojawić się w treści"

        message = self.get_email('email_polish_3')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body == "Ten tekst powinien pojawić się w treści"

        message = self.get_email('email_polish_4')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body == "Ten tekst powinien pojawić się w treści"

        message = self.get_email('email_greek_1')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body.endswith("Από τον Άδη")

        message = self.get_email('email_malformed_thread_header')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)

        assert body.endswith("que cet e-mail est analysé correctement")

        message = self.get_email('email_with_two_headers')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)

        assert body == "This is the main content"

        message = self.get_email('email_portuguese_1')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body == "This is the main body"

        message = self.get_email('email_portuguese_2')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body == "Here is the actual email"

        message = self.get_email('email_portuguese_3')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body.startswith("This is a test")
        assert body.endswith("This should be included")

        message = self.get_email('email_romanian_1')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body == "This is the actual email"

        message = self.get_email('email_german_2')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body == "This is a german email"

        message = self.get_email('email_arabic_3')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body == "مرحبا اريد ١٥٠ دولار لوسمحتي"

    def test_sent_from_device_in_thread(self):
        """
        Tests that if the thread becomes malformed we will be able to parse out the correct part if a sent from device is present
        """
        message = self.get_email("sent_from_device_in_thread")
        body = EmailReplyParser.cut_off_at_signature(message.text)

        assert body == "Yes that would be fine"


    def test_sent_from_device_in_thread_languages(self):
        """
        Tests that if the thread becomes malformed we will be able to parse out the correct part if a sent from device is present
        """
        message_english = self.get_email("sent_from_device_in_thread_english")
        message_hungarian = self.get_email("sent_from_device_in_thread_hungarian")
        message_dutch = self.get_email("sent_from_device_in_thread_dutch")
        message_romanian = self.get_email("sent_from_device_in_thread_romanian")
        message_portuguese = self.get_email("sent_from_device_in_thread_portuguese")
        message_german = self.get_email("sent_from_device_in_thread_german")

        body_english = EmailReplyParser.cut_off_at_signature(message_english.text)
        body_hungarian = EmailReplyParser.cut_off_at_signature(message_hungarian.text)
        body_dutch = EmailReplyParser.cut_off_at_signature(message_dutch.text)
        body_romanian = EmailReplyParser.cut_off_at_signature(message_romanian.text)
        body_portuguese = EmailReplyParser.cut_off_at_signature(message_portuguese.text)
        body_german = EmailReplyParser.cut_off_at_signature(message_german.text)

        assert body_english == "Yes that would be fine"
        assert body_hungarian == "Yes that would be fine"
        assert body_dutch == "Yes that would be fine"
        assert body_romanian == "Yes that would be fine"
        assert body_portuguese == "Yes o Would like the price ajustament of 26€ and i Will keep the boots"
        assert body_german == "Hallo.Bis heute weis ich nicht ob diese Creolie welche ich habe nicht bekommen sind mir gut geschrieben LgElisabeth"

    def test_remove_non_alphabetic_signature_patter(self):
        """
        Tests that we we pick up things like --- and  * * * as signatures and ignore bullets
        """

        message_stars_signoff = self.get_email("email_with_stars_signoff")
        body = EmailReplyParser.cut_off_at_signature(message_stars_signoff.text)
        assert body.endswith("Jim")

        message_dash_signoff = self.get_email("email_signature")
        body = EmailReplyParser.cut_off_at_signature(message_dash_signoff.text)
        assert body.endswith("Perrin Aybara")

        message_bullets = self.get_email("email_bullets")
        body = EmailReplyParser.cut_off_at_signature(message_bullets.text)
        assert body.endswith("another")

    def test_remove_quoted_text(self):
        """Tests that we cut off an email correctly once we see quoted text '>'"""
        message = self.get_email("email_with_quoted_text")
        body = EmailReplyParser.cut_off_at_signature(message.text)
        assert body.endswith("Tony")

    def test_spanish_signoff(self):
        """
        Tests that we're parsing the 'On Jan 31 X wrote:' correctly in Spanish.
        """
        message = self.get_email('spanish_signoff')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body.endswith('Salud')

    def test_remove_header_warnings(self):
        """
        Tests that we remove any warnings about external emails at the top of emails
        """
        message = self.get_email('email_with_header_warning')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body.startswith('Hi,')
        assert body.endswith('Thanks')


    def test_dont_cut_signature_at_start_of_email(self):
        """
        Some e-emails will start with things like "Dear Mr. Best,\n\nHow are you?" these can get parsed out at the end
        of an email unless handled correctly. This test just makes sure that we handle those correctly.
        """
        first_message = self.get_email("george_best")
        second_message = self.get_email("dutch_beste_example")

        body_first_message = EmailReplyParser.cut_off_at_signature(first_message.text)
        body_second_message = EmailReplyParser.cut_off_at_signature(second_message.text)

        assert body_first_message.startswith("Dear George Best,")
        assert body_first_message.endswith("Phil")
        assert body_second_message.startswith("Beste,")
        assert body_second_message.endswith("Timmy")

    def test_french_sign_off(self):
        """
        Tests that we're parsing the 'On Jan 31 X wrote:' correctly in french.
        """

        message = self.get_email('french_signoff')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        assert body.endswith('Il est signalé site innaxecible')

    def test_german_sign_off(self):
        """
        Tests that we're parsing the 'On Jan 31 X wrote:' correctly in german.
        """

        first_message = self.get_email('german_signoff')
        second_message = self.get_email('german_signoff_2')
        body_first_message = EmailReplyParser.cut_off_at_signature(first_message.text, include=True)
        body_second_message = EmailReplyParser.cut_off_at_signature(second_message.text, include=True)
        assert body_first_message.endswith('Mit freundlichen Grüßen')
        assert body_second_message.endswith('Freundliche Grüße')

    def test_orginal_message_sign_off(self):
        """
        Tests that we're parsing the following correctly in german/french/english:
         ---- Original Message ----
        --------- Ursprungliche Nachricht ---------
         ----Original-Nachricht----
         ---------- Forwarded message ---------
        """
        first_message = self.get_email('original_message_german')
        second_message = self.get_email('original_message_german_2')
        third_message = self.get_email('forwarded_message_french')
        body_first_message = EmailReplyParser.cut_off_at_signature(first_message.text, include=True)
        body_second_message = EmailReplyParser.cut_off_at_signature(second_message.text, include=True)
        body_third_message = EmailReplyParser.cut_off_at_signature(third_message.text, include=True)
        assert body_first_message.endswith('Mit freundlichen Grüßen')
        assert body_second_message.endswith('Mit freundlichen Grüßen')
        assert body_third_message.endswith('Bonne fin de journée')

    def test_sincerely_signoff(self):
        """
        Tests that we correctly ignore any "sincerely" mentions, unless they are clearly a signoff
        """

        sincerely_message = self.get_email('sincerely_message')
        body = EmailReplyParser.cut_off_at_signature(sincerely_message.text, include=True)

        assert body.endswith("Paul")


    def test_best_signoff(self):
        """
        Tests that we correctly ignore any "best" mentions, unless they are clearly a signoff
        """

        sincerely_message = self.get_email('best_example')
        body = EmailReplyParser.cut_off_at_signature(sincerely_message.text, include=True)

        assert body.endswith("Paul")

    def test_bottom_posting_headers_preserved(self):
        """
        Tests that customer messages are preserved when using bottom-posting style, where the
        quoted email headers (e.g. **Gesendet/Von/An/Betreff** in German Outlook) appear at the
        very top of the body and the customer's actual reply appears below them.

        Regression test for WATS-339: Bet-At-Home Zendesk interactions where email replies after
        a closed chat session were stored as empty messages because the parser treated the leading
        Gesendet/Von/An/Betreff header block as a quote separator and hid everything below it.
        """
        message = self.get_email('bet_at_home_bottom_posting')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True, word_limit=None)

        assert 'Guten Tag,' in body
        assert 'Ich werde keine Fotos meiner Kreditkarte machen' in body
        assert body != ''

    def test_vielen_dank_courtesy_phrase_not_treated_as_signoff(self):
        """
        Tests that "vielen Dank für Ihre Anfrage!" in the opening of an agent reply is NOT
        treated as a sign-off by EMAIL_SIGNOFF_REGEX, which would cause the rest of the
        message body to be truncated.

        Regression test for WATS-339 (follow-up): Bet-At-Home agent replies opening with
        "vielen Dank für Ihre Anfrage!" had all content after the first sentence stripped
        because "Vielen Dank" matched the sign-off regex with the .{0,20} group allowing
        "für Ihre Anfrage!" as a suffix.
        """
        message = self.get_email('vielen_dank_mid_message')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True, word_limit=None)

        assert 'vielen Dank für Ihre Anfrage!' in body
        assert 'Wäre schön, wenn wir Ihnen damit eine kleine Freude machen.' in body
        assert 'Sollten Sie Fragen haben, stehen wir selbstverständlich gerne zur Verfügung.' in body


    def test_bold_separator_footer_stripped(self):
        """
        Tests that a bold dot-separator line (``**. . . . . . . . . .**``) used by bet-at-home
        as an email footer divider is treated as a signature delimiter, hiding the branding
        footer that follows it from the parsed reply.

        Regression test for WATS-339: the footer block (logo, legal text, ticket reference)
        was appearing in the visible reply because ``SENT_FROM_DEVICE_REGEX`` did not match
        the ``**. . . . . . . . . .**`` separator line.
        """
        message = self.get_email('bet_at_home_footer_separator')
        body = EmailReplyParser.parse_reply(message.text)

        assert 'Ich werde keine Fotos' in body
        assert 'bet-at-home.com Internet Ltd.' not in body
        assert '**. . . . . . . . . .**' not in body
        assert '4Y5JPX' not in body

    def test_single_subject_line_above_reply_stripped(self):
        """
        Tests that a lone ``Subject:`` line above the reply (as Salesforce stores email bodies) is stripped rather than
        treated as a header that hides the reply below it, while the quoted thread is still cut.
        """
        text = self.get_email_text('subject_line_reply')
        body = EmailReplyParser.cut_off_at_signature(text, include=True, word_limit=None)

        assert body.startswith('Hello,\n\nI have uploaded the guarantor form')
        assert body.endswith('Jane Example')
        assert 'Subject:' not in body
        assert 'We still need a guarantor form' not in body

    def test_forward_without_new_text_keeps_forwarded_message(self):
        """
        Tests that when nothing but a divider or a "Sent from ..." line precedes the first forward boundary, the
        forwarded message is kept as the reply with its boundary line and header block removed, with or without
        ``own_domains``.
        """
        expected_content = {
            'original_message_no_reply': 'My tenancy ended on 31 July',
            'forwarded_message_no_reply': 'The boiler has stopped working again',
            'outlook_divider_no_reply': "I paid this month's rent yesterday",
            'outlook_device_line_no_reply': 'We moved in today and noticed the inventory',
        }
        for name, content in expected_content.items():
            for own_domains in (None, ['company.example']):
                with self.subTest(name=name, own_domains=own_domains):
                    text = self.get_email_text(name)
                    body = EmailReplyParser.cut_off_at_signature(text, include=True, word_limit=None,
                                                                 own_domains=own_domains)

                    assert body.startswith('Hello,\n\n' + content), body
                    assert body.endswith('Jane Example'), body
                    for boundary in ('From:', 'Subject:', '____', '----', 'Sent from Outlook'):
                        assert boundary not in body, body

    def test_quote_without_new_text_kept_only_with_own_domains(self):
        """
        Tests that a message below an ``On ... wrote:`` quote marker with nothing written above it stays blank unless
        ``own_domains`` is given and the quoted sender is outside them, since such a quote is usually the other
        side's message.
        """
        text = self.get_email_text('quote_header_no_reply')
        self.assertEqual('', EmailReplyParser.cut_off_at_signature(text, include=True, word_limit=None))

        body = EmailReplyParser.cut_off_at_signature(text, include=True, word_limit=None,
                                                     own_domains=['company.example'])
        assert body.startswith('Hello,\n\nI would like to give notice on my tenancy'), body
        assert body.endswith('Jane Example'), body
        assert 'wrote:' not in body, body

    def test_nested_forward_header_block_with_non_standard_lines_stripped(self):
        """
        Tests that a forward of a forward is reduced to its content when the back-to-back header blocks contain lines
        that are not standard headers (a custom ``Ref ID:`` field, a wrapped ``Cc:`` address list).
        """
        text = self.get_email_text('nested_forward_header_block')
        body = EmailReplyParser.cut_off_at_signature(text, include=True, word_limit=None)

        assert body.startswith("Dear Referencing Team,\n\nI have sent my employer's details twice now"), body
        assert body.endswith('Jane Example'), body
        for header in ('Ref ID:', 'Importance:', 'agent.desk@example.com', 'awaiting your employer'):
            assert header not in body, body

    def test_header_like_line_after_header_block_preserved(self):
        """
        Tests that a ``Label:`` line or an email address directly below a header block is kept as reply text, since
        only lines with a recognised header below them are treated as part of the block.
        """
        for first_reply_line in ('Move-in date: next Friday', 'Viewing at 10:30 suits me',
                                 'Please reply to jane.example@example.com'):
            with self.subTest(first_reply_line=first_reply_line):
                text = ('From: Jane Example <jane.example@example.com>\nSubject: Keys\n' + first_reply_line
                        + '\nWhere should I collect the keys?\n')
                self.assertEqual(first_reply_line + '\nWhere should I collect the keys?',
                                 EmailReplyParser.parse_reply(text).strip())

    def test_header_like_reply_line_above_quoted_headers_preserved(self):
        """
        Tests that a ``Label:`` reply line separated by a blank line from the quoted headers below it is kept rather
        than absorbed into the header block above it.
        """
        text = ('Subject: Keys\n\nCollection time: 10am works for me\n\n'
                'From: Lettings Team <lettings@example.com>\nSent: Monday, 3 August 2026 09:15\n\nCan you do 10am?\n')
        self.assertEqual('Collection time: 10am works for me', EmailReplyParser.parse_reply(text).strip())

    def test_forward_without_new_text_still_cuts_older_thread(self):
        """
        Tests that only the first forwarded message is kept when it carries an older quoted thread of its own.
        """
        text = (
            '-----Original Message-----\n'
            'From: Jane Example <jane.example@example.com>\n'
            'Sent: Monday, 3 August 2026 09:15\n'
            'To: Lettings Team <lettings@example.com>\n'
            'Subject: Keys\n'
            '\n'
            'Where should I return the keys?\n'
            '\n'
            'On Fri, 31 Jul 2026 at 10:00, Lettings Team <lettings@example.com> wrote:\n'
            'Your tenancy ends today.\n'
        )
        self.assertEqual('Where should I return the keys?', EmailReplyParser.parse_reply(text))

    def test_reply_above_quote_boundary_still_cuts_quote(self):
        """
        Tests that a reply written above a quote boundary is still the only part kept.
        """
        texts = [
            ('Thanks, that works for me.\n\n-----Original Message-----\nFrom: Lettings Team <lettings@example.com>\n'
             'Subject: Viewing\n\nCan you do Tuesday?\n'),
            ('Thanks, that works for me.\n________________________________\n'
             'From: Lettings Team <lettings@example.com>\nSent: Monday, 3 August 2026 09:15\nSubject: Viewing\n\n'
             'Can you do Tuesday?\n'),
            ('Thanks, that works for me.\n\nOn Mon, 3 Aug 2026 at 09:15, Lettings Team <lettings@example.com> wrote:\n'
             'Can you do Tuesday?\n'),
        ]
        for text in texts:
            with self.subTest(text=text):
                self.assertEqual('Thanks, that works for me.', EmailReplyParser.parse_reply(text))

    def test_reply_opening_with_short_header_word_preserved(self):
        """
        Tests that a reply whose first word is also a short header keyword is not stripped as a header line.
        """
        openings = ('A quick question about my deposit.', 'De toute facon, je pars demain.', 'To the team, thanks.')
        for opening in openings:
            with self.subTest(opening=opening):
                text = opening + '\n\nOn Mon, 3 Aug 2026 at 09:15, Lettings Team <lettings@example.com> wrote:\nHi\n'
                self.assertEqual(opening, EmailReplyParser.parse_reply(text))

    def test_single_short_keyword_header_line_does_not_blank_reply(self):
        """
        Tests that a reply opening with a header-like line using a short keyword (``A:``, ``De:``, ``To:``), which the
        ordinary parse reads as a header hiding everything below it, still keeps the text below that line.
        """
        for first_line in ('A: yes, please go ahead', 'De: mon cote tout va bien', 'To: the lettings team'):
            with self.subTest(first_line=first_line):
                text = first_line + '\n\nThe rest of my reply.'
                self.assertEqual('The rest of my reply.', EmailReplyParser.parse_reply(text))

    def test_reply_with_content_unchanged_from_ordinary_parse(self):
        """
        Tests that a reply the ordinary parse finds content in, including one opening with a short header word, is
        returned exactly as the ordinary parse gives it.
        """
        texts = [
            ('Thanks, that works for me.\n\n'
             'On Mon, 3 Aug 2026 at 09:15, Lettings Team <lettings@example.com> wrote:\nHi\n'),
            ('A quick question about my deposit.\n\n'
             'From: Lettings Team <lettings@example.com>\nSubject: Deposit\n\nHi\n'),
        ]
        for text in texts:
            with self.subTest(text=text):
                reply = EmailReplyParser.parse_reply(text, own_domains=['example.com'])
                self.assertEqual(text.split('\n')[0], reply)
                self.assertEqual(EmailMessage(text).read().reply, reply)

    def test_subject_line_above_forwarded_marker_keeps_forwarded_message(self):
        """
        Tests that a lone ``Subject:`` line directly above a forwarded-message marker, with nothing written, keeps the
        forwarded message as the reply.
        """
        text = ('Subject: Fwd: Boiler\n---------- Forwarded message ---------\n'
                'From: Jane Example <jane.example@example.com>\nDate: Wed, 5 Aug 2026 at 11:20\nSubject: Boiler\n\n'
                'The boiler has stopped working again.\n')
        self.assertEqual('The boiler has stopped working again.', EmailReplyParser.parse_reply(text).strip())

    def test_own_domains_decides_whether_quoted_or_forwarded_message_is_kept(self):
        """
        Tests the ``own_domains`` rule on a blank reply: a quoted message is kept only when ``own_domains`` is given
        and its sender is outside them; a forwarded message is kept unless its sender is inside them. A sender in a
        subdomain, in any letter case, or with no email address at all counts as inside; a domain that merely ends
        with an own domain's name does not. A single domain string is accepted, and a reply written above an
        own-domain quote is kept as before.
        """
        body = 'Your deposit has been returned.'
        kept = body

        def quote(sender):
            return 'Sent from my iPhone\n\nOn Mon, 3 Aug 2026 at 09:15, ' + sender + ' wrote:\n' + body + '\n'

        def forward(sender, divider='________________________________\n'):
            return divider + 'From: ' + sender + '\nSent: Monday, 3 August 2026 09:15\nSubject: Deposit\n\n' + body + '\n'

        # A header block at the top with no divider, in a shape the ordinary parse does not strip itself.
        start_block = 'From: Lettings Team <lettings@company.example>\nDate: Mon, 3 Aug 2026\nSubject: Deposit\n\n' + body

        cases = [
            (quote('Support <help@company.example>'), ['other.example'], kept),
            (quote('Support <help@company.example>'), ['company.example'], ''),
            (quote('Support <help@company.example>'), 'company.example', ''),
            (quote('Lettings Team'), ['company.example'], ''),
            (forward('Agent <agent@mail.company.example>'), ['other.example'], kept),
            (forward('Agent <agent@mail.company.example>'), ['company.example'], ''),
            (forward('Agent <agent@Company.Example>'), ['company.example'], ''),
            (forward('Jane <jane@notcompany.example>'), ['company.example'], kept),
            (start_block, None, kept),
            (start_block, ['other.example'], kept),
            (start_block, ['company.example'], ''),
            (forward('Lettings Team'), None, kept),
            (forward('Lettings Team'), ['company.example'], ''),
            (forward('Jane Example <\njane@example.com>'), ['company.example'], kept),
            (forward('Jane Example <\nlettings@company.example>'), ['company.example'], ''),
            ('Thanks, that works for me.\n\n' + quote('Support <help@company.example>'), ['company.example'],
             'Thanks, that works for me.'),
        ]
        for text, own_domains, expected in cases:
            with self.subTest(text=text, own_domains=own_domains):
                self.assertEqual(expected, EmailReplyParser.cut_off_at_signature(text, own_domains=own_domains))

    def test_own_domains_unset_keeps_forward_but_not_quote(self):
        """
        Tests that without ``own_domains`` a forwarded message with no new text above it is kept whoever sent it,
        while a message below an ``On ... wrote:`` quote marker stays blank, since it is usually the other side's.
        """
        forward = ('Sent from my iPhone\n\n________________________________\nFrom: Support <help@company.example>\n'
                   'Sent: Monday, 3 August 2026 09:15\nSubject: Deposit\n\nYour deposit has been returned.\n')
        quote = ('Sent from my iPhone\n\nOn Mon, 3 Aug 2026 at 09:15, Support <help@company.example> wrote:\n'
                 'Your deposit has been returned.\n')
        for own_domains in (None, []):
            with self.subTest(own_domains=own_domains):
                self.assertEqual('Your deposit has been returned.',
                                 EmailReplyParser.cut_off_at_signature(forward, own_domains=own_domains))
                self.assertEqual('', EmailReplyParser.cut_off_at_signature(quote, own_domains=own_domains))

    def test_boundary_without_sender_line_kept_with_own_domains(self):
        """
        Tests that ``own_domains`` does not affect a boundary with no sender line: a divider above a header block with
        no ``From:`` line, or a lone ``Subject:`` line above a reply.
        """
        text = ('Sent from my iPhone\n\n-----Original Message-----\nSent: Monday, 3 August 2026 09:15\n'
                'Subject: Deposit\n\nYour deposit has been returned.\n')
        self.assertEqual('Your deposit has been returned.',
                         EmailReplyParser.cut_off_at_signature(text, own_domains=['company.example']))

        text = self.get_email_text('subject_line_reply')
        body = EmailReplyParser.cut_off_at_signature(text, include=True, word_limit=None,
                                                     own_domains=['company.example'])
        assert body.startswith('Hello,\n\nI have uploaded the guarantor form'), body
        assert body.endswith('Jane Example'), body


if __name__ == '__main__':
    unittest.main()

