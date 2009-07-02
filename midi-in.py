def main(*arguments):
    input = file('/dev/midi')
    from Midi import alsaport
    output = alsaport.AlsaPort()
    try:
        while True:
            byte = ord(input.read(1))
            if byte in (0xf8, 0xfe):
                continue
            if byte & 0xf0 == 0x90:
                channel = byte & 0x0f
                pitch = ord(input.read(1))
                velocity = ord(input.read(1))
                output.note_on(None, channel, pitch, velocity)
    except KeyboardInterrupt:
        output.close()

if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
