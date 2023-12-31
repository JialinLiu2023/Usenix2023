


import hashlib
import re


class TamperEvidentFile(object):
    


    def __init__(self, filename):
        self.filename = filename

    def write(self, text, hashline=b"
        u

        if not text.endswith(b"\n"):
            text += b"\n"

        actual_hash = hashlib.sha1(text).hexdigest()

        with open(self.filename, "wb") as f:
            f.write(text)
            f.write(hashline.decode("utf8").format(actual_hash).encode("utf8"))
            f.write(b"\n")

    def validate(self):
        


        with open(self.filename, "rb") as f:
            text = f.read()

        start_last_line = text.rfind(b"\n", 0, -1)
        if start_last_line == -1:
            return False

        original_text = text[:start_last_line+1]
        last_line = text[start_last_line+1:]

        expected_hash = hashlib.sha1(original_text).hexdigest().encode('utf8')
        match = re.search(b"[0-9a-f]{40}", last_line)
        if not match:
            return False
        actual_hash = match.group(0)
        return actual_hash == expected_hash
