import sys
import os
from email_reply_parser import EmailReplyParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def get_email(name):
    """ Return EmailMessage instance
    """
    with open('emails/%s.txt' % name) as f:
        text = f.read()
    return text


def test_include_true():
    text = get_email('email_signature')
    body = EmailReplyParser.cut_off_at_signature(text, include=True, word_limit=100)
    assert body[68:81] == 'Kind regards,'


def test_include_false():
    text = get_email('email_signature')
    body = EmailReplyParser.cut_off_at_signature(text, include=False, word_limit=100)
    assert body.endswith('email cut-off point.\n\n')


def test_include_true_german():
    text = get_email('email_german')
    body = EmailReplyParser.cut_off_at_signature(text, include=True, word_limit=100)
    assert body[81:106] == 'Mit freundlichen Grussen,'


def test_include_false_german():
    text = get_email('email_german')
    body = EmailReplyParser.cut_off_at_signature(text, include=False, word_limit=100)
    assert body.endswith('November vornehmen.\n\n')


def test_cut_off_default():
    text = get_email('long_passage')
    body = EmailReplyParser.cut_off_at_signature(text, word_limit=100)
    assert body.endswith('"Now fax quiz Jack! " my')


def test_cut_off_10_words():
    text = get_email('long_passage')
    body = EmailReplyParser.cut_off_at_signature(text, word_limit=10)
    assert body.endswith('a lazy dog. DJs')


def test_cut_off_500_words():
    text = get_email('long_passage')
    body = EmailReplyParser.cut_off_at_signature(text, word_limit=500)
    assert body.endswith('Joaquin Phoenix was')

test_include_true()