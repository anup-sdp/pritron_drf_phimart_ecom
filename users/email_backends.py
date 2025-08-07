# custom email backend to fix ssl.SSLCertVerificationError while sending email, in windows with python 3.13

import ssl
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

class CustomEmailBackend(SMTPBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.use_tls or self.use_ssl:
            self.ssl_context = ssl.create_default_context()
            try:
                self.ssl_context.verify_flags &= ~ssl.VERIFY_X509_STRICT
            except AttributeError:
                pass  # VERIFY_X509_STRICT not available, no action needed

