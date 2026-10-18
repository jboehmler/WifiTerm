class RawTermWindows:
    import msvcrt

    def get_key(self):
        return self.msvcrt.get_key()
