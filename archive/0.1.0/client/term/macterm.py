class RawTermMacCarbon:
    import Carbon

    def get_key(self):
        if self.Carbon.Evt.EventAvail(0x0008)[0] == 0:  # 0x0008 is the keyDownMask
            return ""
        else:
            (
                what,
                msg,
                when,
                where,
                mod,
            ) = self.Carbon.Evt.GetNextEvent(
                0x0008
            )[1]
            return chr(msg & 0x000000FF)
