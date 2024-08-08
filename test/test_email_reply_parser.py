import os
import sys
import unittest
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from email_reply_parser import EmailReplyParser


def get_email(name):
    """Return EmailMessage instance, utility function"""
    text = Path(f'emails/{name}.txt').read_text()
    return EmailReplyParser.read(text)

def get_email_text(name):
    """Return file text only"""
    return Path(f'emails/{name}.txt').read_text()


class EmailMessageTest(unittest.TestCase):
    def test_simple_body(self):
        message = get_email('email_1_1')

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
        message = get_email('email_1_6')
        self.assertTrue('I get' in message.fragments[0].content)
        self.assertTrue('Sent' in message.fragments[1].content)

    def test_complex_body_with_one_fragment(self):
        message = get_email('email_1_5')

        self.assertEqual(1, len(message.fragments))

    def test_verify_reads_signature_correct(self):
        message = get_email('correct_sig')
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
        msg = get_email('email_1_7')
        self.assertTrue(':+1:' in msg.fragments[0].content)

    def test_reply_from_gmail(self):
        message = get_email_text('email_gmail')
        EmailReplyParser.parse_reply(message)

    def test_parse_out_just_top_for_outlook_reply(self):
        message = get_email_text('email_2_1')
        self.assertEqual("Outlook with a reply", EmailReplyParser.parse_reply(message))

    def test_parse_out_just_top_for_outlook_with_reply_directly_above_line(self):
        message = get_email_text('email_2_2')
        self.assertEqual("Outlook with a reply directly above line", EmailReplyParser.parse_reply(message))

    def test_parse_out_just_top_for_outlook_with_unusual_headers_format(self):
        message = get_email_text('email_2_3')
        self.assertEqual(
            "Outlook with a reply above headers using unusual format",
            EmailReplyParser.parse_reply(message)
        )

    def test_sent_from_iphone(self):
        message = get_email_text('email_iPhone')
        self.assertTrue("Sent from my iPhone" not in EmailReplyParser.parse_reply(message))

    def test_email_one_is_not_on(self):
        message = get_email_text('email_one_is_not_on')
        self.assertTrue(
            "On Oct 1, 2012, at 11:55 PM, Dave Tapley wrote:" not in EmailReplyParser.parse_reply(message)
        )

    def test_partial_quote_header(self):
        message = get_email('email_partial_quote_header')
        self.assertTrue("On your remote host you can run:" in message.reply)
        self.assertTrue("telnet 127.0.0.1 52698" in message.reply)
        self.assertTrue("This should connect to TextMate" in message.reply)

    def test_email_headers_no_delimiter(self):
        message = get_email('email_headers_no_delimiter')
        self.assertEqual(message.reply.strip(), 'And another reply!')

    def test_pathological_emails(self):
        t0 = time.time()
        get_email("pathological")
        self.assertTrue(time.time() - t0 < 1, "Took too long")

    def test_doesnt_remove_signature_delimiter_in_mid_line(self):
        message = get_email('email_sig_delimiter_in_middle_of_line')
        self.assertEqual(1, len(message.fragments))

    def test_clean_email_content_no_change(self):
        # Ensure that a short email with no reply and no signature doesn't change
        message = get_email('email_one_line')
        clean_content = EmailReplyParser.cut_off_at_signature(body=message.text, word_limit=1000)
        self.assertEqual(message.text, clean_content)

    def test_end_of_email(self):
        # Check that an email that continues after the sign-off (without being a header or reply) cuts off at signature
        message = get_email('email_continue_after_signoff')
        body = EmailReplyParser.cut_off_at_signature(message.text)
        self.assertTrue(body.endswith('Tom Bombadil'))

    def test_keep_newlines_when_no_signoff(self):
        # Test that when there is no sign-off message detected at the end, the newlines/spacing are not changed
        message = get_email('email_no_signature')
        body = EmailReplyParser.cut_off_at_signature(message.text)
        self.assertTrue(body.endswith("Let's see if it works.\n\nK"))

    def test_remove_header_warnings(self):
        """
        Tests that we remove any warnings about external emails at the top of emails
        """
        message = get_email('email_with_header_warning')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body.startswith('Hi,'))
        self.assertTrue(body.endswith('Thanks'))


    def test_dont_cut_signature_at_start_of_email(self):
        """
        Some e-emails will start with things like "Dear Mr. Best,\n\nHow are you?" these can get parsed out at the end
        of an email unless handled correctly. This test just makes sure that we handle those correctly.
        """
        first_message = get_email("george_best")
        second_message = get_email("dutch_beste_example")

        body_first_message = EmailReplyParser.cut_off_at_signature(first_message.text)
        body_second_message = EmailReplyParser.cut_off_at_signature(second_message.text)

        self.assertTrue(body_first_message.startswith("Dear George Best,"))
        self.assertTrue(body_first_message.endswith("Phil"))
        self.assertTrue(body_second_message.startswith("Beste,"))
        self.assertTrue(body_second_message.endswith("Timmy"))

    def test_sent_from_device_in_thread(self):
        """
        Tests that if the thread becomes malformed we will be able to parse out the correct part if a sent from device is present
        """
        message = get_email("sent_from_device_in_thread")
        body = EmailReplyParser.cut_off_at_signature(message.text)

        self.assertTrue(body == "Yes that would be fine")

    # -------------------- LANGUAGES -------------------- #

    def test_include_signature_true(self):
        # Test that the cut_off_at_signature function ends an email after the sign-off when include = True
        message_english = get_email('email_signature')
        message_german = get_email('email_german')
        message_french = get_email('email_french')

        body_english = EmailReplyParser.cut_off_at_signature(message_english.text, include=True, word_limit=100)
        body_german = EmailReplyParser.cut_off_at_signature(message_german.text, include=True, word_limit=100)
        body_french = EmailReplyParser.cut_off_at_signature(message_french.text, include=True, word_limit=100)

        self.assertTrue(body_english.endswith('Kind regards,\n\nPerrin Aybara'))
        self.assertTrue(body_german.endswith('Mit freundlichen Grüßen,\n\nLukas'))
        self.assertTrue(body_french.endswith('Bien à vous,\n\nNicolette Baudelaire'))

    def test_include_signature_false(self):
        # Test that the cut_off_at_signature function ends an email before the sign-off when include = False
        message_english = get_email('email_signature')
        message_german = get_email('email_german')
        message_french = get_email('email_french')

        body_english = EmailReplyParser.cut_off_at_signature(message_english.text, include=False, word_limit=100)
        body_german = EmailReplyParser.cut_off_at_signature(message_german.text, include=False, word_limit=100)
        body_french = EmailReplyParser.cut_off_at_signature(message_french.text, include=False, word_limit=100)

        self.assertTrue(body_english.endswith('email cut-off point.'))
        self.assertTrue(body_german.endswith('November vornehmen.'))
        self.assertTrue(body_french.endswith("s'il vous plaît?"))

    def test_word_limit(self):
        # Test that a long email cuts off after the default or given word limit
        message = get_email('long_passage')
        body_default_limit = EmailReplyParser.cut_off_at_signature(message.text, word_limit=100)  # Default value
        body_short = EmailReplyParser.cut_off_at_signature(message.text, word_limit=10)  # Less than default
        body_long = EmailReplyParser.cut_off_at_signature(message.text, word_limit=500)  # More than default

        self.assertTrue(body_default_limit.endswith('"HERE IS ONE HUNDRED!"'))
        self.assertTrue(body_short.endswith('TEN!'))
        self.assertTrue(body_long.endswith('FIVE HUNDRED IS HERE!'))

    def test_clean_email_portuguese(self):
        # Test Portuguese regex
        message = get_email('email_portuguese')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=False, word_limit=100)
        self.assertTrue(body.endswith("Cumprimentos\nPedro Mota"))

    def test_clean_email_french(self):
        # Test Portuguese regex
        message = get_email('email_french_accent_sent_on')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=False, word_limit=100)
        self.assertTrue(body == "Bonjour, ca va bien!")

    def test_remove_SIG_REGEX_end(self):
        # Test that any "Sent from iPhone" messages are removed at the end of an email
        message_french = get_email('email_iphone_french')
        message_portuguese = get_email('email_iphone_portuguese')
        message_polish = get_email('email_iphone_polish')
        message_finnish = get_email('email_iphone_finnish')

        body_french = EmailReplyParser.cut_off_at_signature(message_french.text)
        body_portuguese = EmailReplyParser.cut_off_at_signature(message_portuguese.text)
        body_polish = EmailReplyParser.cut_off_at_signature(message_polish.text)
        body_finnish = EmailReplyParser.cut_off_at_signature(message_finnish.text)

        self.assertTrue(body_french.endswith("Au revoir,\n\nKelsier"))
        self.assertTrue(body_portuguese.endswith("Adeus,\n\nOtis"))
        self.assertTrue(body_polish.endswith("Do widzenia,\n\nTriss"))
        self.assertTrue(body_finnish.endswith("Hyvästi,\n\nTorin"))

    def test_remove_SIG_REGEX_start(self):
        # Test that any "Sent from iPhone" messages are removed at the beginning of an email
        message_english = get_email('email_iphone_start')
        message_german = get_email('email_iphone_start_german')
        body_english = EmailReplyParser.cut_off_at_signature(message_english.text)
        body_german = EmailReplyParser.cut_off_at_signature(message_german.text)
        self.assertTrue(body_english.startswith('Hi,\n\nCase where the'))
        self.assertTrue(body_german.startswith('Hallo,\n\nFall, in dem das'))


    def test_parse_response_headers(self):
        """
        Tests that we are parsing out email response headers correctly for multiple languages
        """
        message = get_email('email_polish_1')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body == "Ten tekst powinien pojawić się w treści")

        message = get_email('email_polish_2')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body == "Ten tekst powinien pojawić się w treści")

        message = get_email('email_polish_3')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body == "Ten tekst powinien pojawić się w treści")

        message = get_email('email_polish_4')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body == "Ten tekst powinien pojawić się w treści")

        message = get_email('email_greek_1')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body.endswith("Από τον Άδη"))

        message = get_email('email_malformed_thread_header')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body.endswith("que cet e-mail est analysé correctement"))

        message = get_email('email_with_two_headers')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body == "This is the main content")

        message = get_email('email_portuguese_1')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body == "This is the main body")

        message = get_email('email_portuguese_2')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body == "Here is the actual email")

        message = get_email('email_portuguese_3')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body.startswith("This is a test"))
        self.assertTrue(body.endswith("This should be included"))

        message = get_email('email_romanian_1')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body == "This is the actual email")

        message = get_email('email_german_2')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body == "This is a german email")


    def test_sent_from_device_in_thread_languages(self):
        """
        Tests that if the thread becomes malformed we will be able to parse out the correct part if a sent from device is present
        """
        message_english = get_email("sent_from_device_in_thread_english")
        message_hungarian = get_email("sent_from_device_in_thread_hungarian")
        message_dutch = get_email("sent_from_device_in_thread_dutch")
        message_romanian = get_email("sent_from_device_in_thread_romanian")

        body_english = EmailReplyParser.cut_off_at_signature(message_english.text)
        body_hungarian = EmailReplyParser.cut_off_at_signature(message_hungarian.text)
        body_dutch = EmailReplyParser.cut_off_at_signature(message_dutch.text)
        body_romanian = EmailReplyParser.cut_off_at_signature(message_romanian.text)

        self.assertTrue(body_english == "Yes that would be fine")
        self.assertTrue(body_hungarian == "Yes that would be fine")
        self.assertTrue(body_dutch == "Yes that would be fine")
        self.assertTrue(body_romanian == "Yes that would be fine")

    def test_remove_non_alphabetic_signature_patter(self):
        """
        Tests that we we pick up things like --- and  * * * as signatures and ignore bullets
        """

        message_stars_signoff = get_email("email_with_stars_signoff")
        body = EmailReplyParser.cut_off_at_signature(message_stars_signoff.text)
        self.assertTrue(body.endswith("Jim"))

        message_dash_signoff = get_email("email_signature")
        body = EmailReplyParser.cut_off_at_signature(message_dash_signoff.text)
        self.assertTrue(body.endswith("Perrin Aybara"))

        message_bullets = get_email("email_bullets")
        body = EmailReplyParser.cut_off_at_signature(message_bullets.text)
        self.assertTrue(body.endswith("another"))

    def test_remove_quoted_text(self):
        """Tests that we cut off an email correctly once we see quoted text '>'"""
        message = get_email("email_with_quoted_text")
        body = EmailReplyParser.cut_off_at_signature(message.text)
        self.assertTrue(body.endswith("Tony"))

    def test_spanish_signoff(self):
        """
        Tests that we're parsing the 'On Jan 31 X wrote:' correctly in Spanish.
        """
        message = get_email('spanish_signoff')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True)
        self.assertTrue(body.endswith('Salud'))


if __name__ == '__main__':
    unittest.main()
