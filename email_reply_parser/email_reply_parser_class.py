from typing import Optional

from .email_message import EmailMessage


class EmailReplyParser(object):
    """ Represents an email message that is parsed.
    """

    @staticmethod
    def read(text):
        """ Factory method that splits email into list of fragments

            :param text: A string email body
            :returns: EmailMessage instance
        """
        return EmailMessage(text).read()

    @staticmethod
    def parse_reply(text):
        """ Provides the reply portion of email.

            :param text: A string email body
            :returns: Reply body message
        """
        return EmailReplyParser.read(text).reply

    @staticmethod
    def cut_off_at_signature(body: str, include_signature: Optional[bool] = True, word_limit: Optional[int] = 100):
        """
        Remove the signature section from an email, and use the email Reply Parser to try to remove any
        "thread" content.
        Languages supported: English, French, German, Romanian, Spanish, Italian.

        :param body: The email string to be parsed and cleaned.
        :param include_signature: Include signature at the end or cut it off. Defaults to True.
        :param word_limit: If we set the word-limit to None the string will not be split and line breaks will
        be retained. If a word-limit is set, the email will be cut-off after that limit if a signature is not
        found before that point. Default = 100.
        """
        parsed_email = EmailReplyParser.parse_reply(body)
        cleaned_email = EmailMessage.clean_email_content(parsed_email, include_signature, word_limit)
        return cleaned_email.strip()