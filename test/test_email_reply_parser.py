import os
import sys
import unittest
import re
import time
from email_reply_parser import EmailReplyParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class EmailMessageTest(unittest.TestCase):
    def test_simple_body(self):
        message = self.get_email('email_1_1')

        self.assertEqual(3, len(message.fragments))
        self.assertEqual(
            [False, True, True],
            [f.signature for f in message.fragments]
        )
        self.assertEqual(
            [False, True, True],
            [f.hidden for f in message.fragments]
        )
        self.assertTrue("folks" in message.fragments[0].content)
        self.assertTrue("riak-users" in message.fragments[2].content)

    def test_reads_bottom_message(self):
        message = self.get_email('email_1_2')

        self.assertEqual(6, len(message.fragments))
        self.assertEqual(
            [False, True, False, True, False, False],
            [f.quoted for f in message.fragments]
        )

        self.assertEqual(
            [False, False, False, False, False, True],
            [f.signature for f in message.fragments]
        )

        self.assertEqual(
            [False, False, False, True, True, True],
            [f.hidden for f in message.fragments]
        )

        self.assertTrue("Hi," in message.fragments[0].content)
        self.assertTrue("On" in message.fragments[1].content)
        self.assertTrue(">" in message.fragments[3].content)
        self.assertTrue("riak-users" in message.fragments[5].content)

    def test_reads_inline_replies(self):
        message = self.get_email('email_1_8')
        self.assertEqual(7, len(message.fragments))

        self.assertEqual(
            [True, False, True, False, True, False, False],
            [f.quoted for f in message.fragments]
        )

        self.assertEqual(
            [False, False, False, False, False, False, True],
            [f.signature for f in message.fragments]
        )

        self.assertEqual(
            [False, False, False, False, True, True, True],
            [f.hidden for f in message.fragments]
        )

    def test_reads_top_post(self):
        message = self.get_email('email_1_3')

        self.assertEqual(5, len(message.fragments))

    def test_multiline_reply_headers(self):
        message = self.get_email('email_1_6')
        self.assertTrue('I get' in message.fragments[0].content)
        self.assertTrue('Sent' in message.fragments[1].content)

    def test_captures_date_string(self):
        message = self.get_email('email_1_4')

        self.assertTrue('Awesome' in message.fragments[0].content)
        self.assertTrue('On' in message.fragments[1].content)
        self.assertTrue('Loader' in message.fragments[1].content)

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
        self.assertTrue('On' in msg.fragments[1].content)
        self.assertTrue('Steps 0-2' in msg.fragments[1].content)

    def test_reply_is_parsed(self):
        message = self.get_email('email_1_2')
        self.assertTrue("You can list the keys for the bucket" in message.reply)

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

    def test_multiple_on(self):
        message = self.get_email("greedy_on")
        self.assertTrue(re.match('^On your remote host', message.fragments[0].content))
        self.assertTrue(re.match('^On 9 Jan 2014', message.fragments[1].content))

        self.assertEqual(
            [False, True, False],
            [fragment.quoted for fragment in message.fragments]
        )

        self.assertEqual(
            [False, False, False],
            [fragment.signature for fragment in message.fragments]
        )

        self.assertEqual(
            [False, True, True],
            [fragment.hidden for fragment in message.fragments]
        )

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

    def test_include_signature_true(self):
        # Test that the cut_off_at_signature function ends the email after the sign-off for include = True
        message = self.get_email('email_signature')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True, word_limit=100)
        assert body.endswith('Kind regards,\n\nPerrin Aybara')

    def test_include_signature_false(self):
        # Test that the cut_off_at_signature function ends the email before the sign-off for include = False
        message = self.get_email('email_signature')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=False, word_limit=100)
        assert body.endswith('email cut-off point.')

    def test_word_limit_default(self):
        # Test that a long email with no word_limit provided cuts off after 100 words
        message = self.get_email('long_passage')
        body = EmailReplyParser.cut_off_at_signature(message.text, word_limit=100)
        assert body.endswith('"HERE IS ONE HUNDRED!"')

    def test_word_limit_10_words(self):
        # Test again for a word_limit of 10
        message = self.get_email('long_passage')
        body = EmailReplyParser.cut_off_at_signature(message.text, word_limit=10)
        assert body.endswith('TEN!')

    def test_word_limit_500_words(self):
        # Test again for a word_limit of 500
        message = self.get_email('long_passage')
        body = EmailReplyParser.cut_off_at_signature(message.text, word_limit=500)
        assert body.endswith('FIVE HUNDRED IS HERE!')

    def test_include_signature_true_german(self):
        # Similar to previous test except for German email
        message = self.get_email('email_german')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True, word_limit=100)
        assert body.endswith('Mit freundlichen Grussen,\n\nLukas')

    def test_include_signature_false_german(self):
        # Similar to previous test except for German email
        message = self.get_email('email_german')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=False, word_limit=100)
        assert body.endswith('November vornehmen.')

    def test_include_signature_true_french(self):
        # Similar to previous test except for French email
        message = self.get_email('email_french')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=True, word_limit=100)
        assert body.endswith('Nicolette Baudelaire')

    def test_include_signature_false_french(self):
        # Similar to previous test except for French email
        message = self.get_email('email_french')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=False, word_limit=100)
        assert body.endswith("s'il vous plait?")

    def test_clean_email_portuguese(self):
        # Similar to previous test except for French email
        message = self.get_email('email_portuguese')
        body = EmailReplyParser.cut_off_at_signature(message.text, include=False, word_limit=100)
        assert body.endswith("Cumprimentos\nPedro Mota")

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


if __name__ == '__main__':
    unittest.main()

