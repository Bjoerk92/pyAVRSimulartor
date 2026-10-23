from . import AVR_Instructions as inc
import ctypes
from dataclasses import dataclass, field
from collections.abc import Callable, Mapping
from types import MappingProxyType

# C = carry flag 
# Z = Zero flag
# N = Negative flag
# V = Two Complement overflow flag
# S = Sign flag
# T = Transfer bit
# I = Global Interrupt Enable Bit


@dataclass
class cpu():
    name : str
    flash : bytearray
    pc : int
    core : str
    missing_instructions : list[str]
    data_memory : bytearray
    registers : Mapping[str, ctypes.c_uint16]
    running: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self.registers = MappingProxyType(dict(self.registers))

    def write_program(self, program : bytearray) -> None:
        if len(program) > len(self.flash):
            raise MemoryError("Program size is larger than flash!")

        self.flash[:len(program)] = program

    def getRegisterNumber(self, name = str) -> ctypes.c_uint16 | None:
        if name in self.registers:
            return self.registers[name]
        else:
            return None 

    def read_register(self, reg_num : int) -> ctypes.c_uint8 :
        return self.data_memory[reg_num]

    def write_register(self, reg_num : int, value : ctypes.c_uint8) -> None :
        self.data_memory[reg_num] = value

    def _fetch(self) -> ctypes.c_uint16:
        """Fetches a 16-bit word from Flash instruction space."""
        # AVR instructions are stored little-endian
        low_byte = self.flash[self.pc]
        high_byte = self.flash[self.pc + 1]
        
        # Advance PC by 2 bytes (one instruction word)
        self.pc += 2
        
        # Combine into a single 16-bit word
        return (high_byte << 8) | low_byte

    def _execute(self, opcode : ctypes.c_uint16, mnemonic : str) -> None :
        handlers : dict[str, Callable[[ctypes.c_uint16], None]] = {
            "NOP": self._nop,
            "LDI": self._ldi,
            "ADD": self._add,
            "CP": self._cp,
            "BREAK": self._break,
        }

        handler = handlers.get(mnemonic)
        if handler is None:
            raise NotImplementedError(f"{mnemonic} is not implemented yet")

        handler(opcode)

    def _nop(self, _opcode : ctypes.c_uint16) -> None:
        pass

    def _ldi(self, opcode : ctypes.c_uint16) -> None:
        value = (opcode & 0x0F) | ((opcode & 0x0F00) >> 4)
        Rd = 16 + ((opcode >> 4) & 0x0F)

        self.write_register(Rd, value)

    def _add(self, opcode : ctypes.c_uint16) -> None:
        Rd = (opcode >> 4) & 0x1F
        Rr = (opcode & 0x0F) | ((opcode >> 5) & 0x10)

        val_Rd = self.read_register(Rd)
        val_Rr = self.read_register(Rr)

        self.write_register(Rd, ((val_Rd+ val_Rr) & 0xFF))

    def _break(self, _opcode : ctypes.c_uint16) -> None:
        self.running = False

    def _cp(self, opcode : ctypes.c_uint16) -> None:
        Rd = (opcode >> 4) & 0x1F
        Rr = (opcode & 0x0F) | ((opcode >> 5) & 0x10)

        val_Rd = self.read_register(Rd)
        val_Rr = self.read_register(Rr)

        # AVR CP compares Rd and Rr by computing Rd - Rr without writing a result back.
        # The subtraction result is only used to update the status flags.
        result = (val_Rd - val_Rr) & 0xFF

        sreg_val = self.read_register(self.registers["SREG"])

        # Z flag: result == 0
        if result == 0:
            sreg_val |= 0x02
        else:
            sreg_val &= ~0x02

        # H flag: carry from bit 3 to 4 in the subtraction (borrow from bit 3)
        if ((val_Rd ^ val_Rr ^ result) & 0x10) != 0:
            sreg_val |= 0x20
        else:
            sreg_val &= ~0x20

        # N flag: most significant bit of the subtraction result.
        if result & 0x80:
            sreg_val |= 0x08
        else:
            sreg_val &= ~0x08

        # V flag: signed overflow for Rd - Rr.
        if ((val_Rd ^ val_Rr) & (val_Rd ^ result) & 0x80) != 0:
            sreg_val |= 0x04
        else:
            sreg_val &= ~0x04

        # S flag: N XOR V.
        if bool(sreg_val & 0x08) != bool(sreg_val & 0x04):
            sreg_val |= 0x40
        else:
            sreg_val &= ~0x40

        # C flag: unsigned borrow from the most significant bit.
        if val_Rd < val_Rr:
            sreg_val |= 0x01
        else:
            sreg_val &= ~0x01

        self.write_register(self.registers["SREG"], sreg_val)

    def step(self) -> None :
        opcode =  self._fetch()
        mnemonic = inc.decode(opcode)
        self._execute(opcode, mnemonic)


@dataclass
class Atmega328p(cpu):
    """ Data class for the Atmega 328p memory and registers"""
    def __init__(self, flashSize: int = 0x8000) -> None:
        """ constructor for the class
        
        Param:
            flashSize: size of the flash. default 0x8000 (32Kb)
        """
        super().__init__(
            name = "ATmega328p",
            flash=bytearray(flashSize),
            pc=0,
            core="AVRe+",
            missing_instructions=["ELPM", "EIJMP", "EICALL"],
            data_memory=bytearray(0x0900),
            # Total size = 2304 bytes.
            # Addressing:
            #   0x0000 - 0x001F: Registers R0 to R31
            #   0x0020 - 0x005F: Standard I/O Registers (like PORTB)
            #   0x0100 - 0x08FF: Internal SRAM
            registers = 
            {
                "R0" : 0x0000,
                "R1" : 0x0001, 
                "R2" : 0x0002, 
                "R3" : 0x0003, 
                "R4" : 0x0004, 
                "R5" : 0x0005, 
                "R6" : 0x0006, 
                "R7" : 0x0007, 
                "R8" : 0x0008, 
                "R9" : 0x0009, 
                "R10": 0x000A,
                "R11": 0x000B,
                "R12": 0x000C,
                "R13": 0x000D,
                "R14": 0x000E,
                "R15": 0x000F,
                "R16": 0x0010,
                "R17": 0x0011,
                "R18": 0x0012,
                "R19": 0x0013,
                "R20": 0x0014,
                "R21": 0x0015,
                "R22": 0x0016,
                "R23": 0x0017,
                "R24": 0x0018,
                "R25": 0x0019,
                "R26": 0x001A,
                "R27": 0x001B,
                "R28": 0x001C,
                "R29": 0x001D,
                "R30": 0x001E,
                "R31": 0x001F,
                "PINB" : 0x0023,
                "DDRB" : 0x0024,
                "PORTB": 0x0025,
                "PINC" : 0x0026,
                "DDRC" : 0x0027,
                "PORTC": 0x0028,
                "PIND" : 0x0029,
                "DDRD" : 0x002A,
                "PORTD": 0x002B,
                "TIFR0": 0x0035,
                "TIFR1": 0x0036,
                "TIFR2": 0x0037,
                "PCIFR": 0x003B,
                "EIFR" : 0x003C,
                "EIMSK": 0x003D,
                "GPIOR0": 0x003E,
                "EECR" : 0x003F,
                "EEDR" : 0x0040,
                "EEARL": 0x0041,
                "EEARH": 0x0042,
                "GTCCR": 0x0043,
                "TCCR0A": 0x0044,
                "TCCR0B": 0x0045,
                "TCNT0": 0x0046,
                "OCR0A": 0x0047,
                "OCR0B": 0x0048,
                "GPIOR1": 0x004A,
                "GPIOR2": 0x004B,
                "SPCR" : 0x004C,
                "SPSR" : 0x004D,
                "SPDR" : 0x004E,
                "ACSR" : 0x0050,
                "SMCR" : 0x0053,
                "MCUSR": 0x0054,
                "MCUCR": 0x0055,
                "SPMCSR": 0x0057,
                "SREG": 0x005F,
                "WDTCSR": 0x0060,
                "CLKPR": 0x0061,
                "PRR"  : 0x0064,
                "OSCCAL": 0x0066,
                "PCICR": 0x0068,
                "EICRA": 0x0069,
                "PCMSK0": 0x006B,
                "PCMSK1": 0x006C,
                "PCMSK2": 0x006D,
                "TIMSK0": 0x006E,
                "TIMSK1": 0x006F,
                "TIMSK2": 0x0070,
                "ADCL" : 0x0078,
                "ADCH" : 0x0079,
                "ADCSRA": 0x007A,
                "ADCSRB": 0x007B,
                "ADMUX": 0x007C,
                "DIDR0": 0x007E,
                "DIDR1": 0x007F,
                "TCCR1A": 0x0080,
                "TCCR1B": 0x0081,
                "TCCR1C": 0x0082,
                "TCNT1L": 0x0084,
                "TCNT1H": 0x0085,
                "ICR1L" : 0x0086,
                "ICR1H" : 0x0087,
                "OCR1AL": 0x0088,
                "OCR1AH": 0x0089,
                "OCR1BL": 0x008A,
                "OCR1BH": 0x008B,
                "TCCR2A": 0x00B0,
                "TCCR2B": 0x00B1,
                "TCNT2": 0x00B2,
                "OCR2A": 0x00B3,
                "OCR2B": 0x00B4,
                "ASSR" : 0x00B6,
                "TWBR" : 0x00B8,
                "TWSR" : 0x00B9,
                "TWAR" : 0x00BA,
                "TWDR" : 0x00BB,
                "TWCR" : 0x00BC,
                "TWAMR": 0x00BD,
                "UCSR0A": 0x00C0,
                "UCSR0B": 0x00C1,
                "UCSR0C": 0x00C2,
                "UBRR0L": 0x00C4,
                "UBRR0H": 0x00C5,
                "UDR0" : 0x00C6,
            }
            
        )


    def __del__(self) -> None:
        pass


        