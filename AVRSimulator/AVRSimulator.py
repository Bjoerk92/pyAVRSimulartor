if __package__:
    from .AVR.AVR_gui import run_gui
else:
    from AVR.AVR_gui import run_gui


if __name__ == "__main__":
    run_gui()
