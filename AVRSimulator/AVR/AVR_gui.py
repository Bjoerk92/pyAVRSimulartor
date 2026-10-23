import tkinter as tk
from tkinter import messagebox, ttk
from collections.abc import Callable

from .AVR_CPU import Atmega328p, cpu


class AVRSimulatorGUI:
    def __init__(
        self,
        root: tk.Tk,
        cpu_factory: Callable[[], cpu] = Atmega328p,
    ) -> None:
        self.root = root
        self.root.title("AVR Simulator")
        self.root.geometry("760x600")

        self.cpu_factory = cpu_factory
        self.cpu = self.cpu_factory()
        self.program = bytearray()
        self.is_running = False

        self._build_ui()
        self._refresh_registers()
        self._set_status("Start a new project or load a program.")

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=1)

        ttk.Label(
            self.root,
            text="Program bytes (hex; spaces/newlines separate bytes, # starts a comment)",
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

        self.program_text = tk.Text(self.root, height=7, wrap="none", undo=True)
        self.program_text.grid(row=1, column=0, sticky="nsew", padx=10)

        self._build_menu()

        controls = ttk.Frame(self.root, padding=(10, 8))
        controls.grid(row=2, column=0, sticky="ew")
        for index in range(5):
            controls.columnconfigure(index, weight=1)

        ttk.Button(controls, text="Load", command=self.load_program).grid(
            row=0, column=0, sticky="ew", padx=3
        )
        ttk.Button(controls, text="Step", command=self.step).grid(
            row=0, column=1, sticky="ew", padx=3
        )
        ttk.Button(controls, text="Run", command=self.run).grid(
            row=0, column=2, sticky="ew", padx=3
        )
        ttk.Button(controls, text="Stop", command=self.stop).grid(
            row=0, column=3, sticky="ew", padx=3
        )
        ttk.Button(controls, text="Reset", command=self.reset).grid(
            row=0, column=4, sticky="ew", padx=3
        )

        state = ttk.Frame(self.root, padding=(10, 0, 10, 8))
        state.grid(row=3, column=0, sticky="ew")
        self.pc_label = ttk.Label(state, text="PC: 0x0000")
        self.pc_label.pack(side="left")
        self.status_label = ttk.Label(state, text="", anchor="e")
        self.status_label.pack(side="right", fill="x", expand=True)

        register_frame = ttk.LabelFrame(self.root, text="Registers", padding=8)
        register_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.root.rowconfigure(4, weight=2)
        register_frame.rowconfigure(0, weight=1)
        register_frame.columnconfigure(0, weight=1)

        self.registers_view = ttk.Treeview(
            register_frame,
            columns=("value", "hex"),
            show="headings",
            height=16,
        )
        self.registers_view.heading("value", text="Value (decimal)")
        self.registers_view.heading("hex", text="Value (hex)")
        self.registers_view.column("value", anchor="center", width=150)
        self.registers_view.column("hex", anchor="center", width=150)
        scrollbar = ttk.Scrollbar(
            register_frame, orient="vertical", command=self.registers_view.yview
        )
        self.registers_view.configure(yscrollcommand=scrollbar.set)
        self.registers_view.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        for number in range(32):
            self.registers_view.insert("", "end", iid=str(number), text=f"R{number}")
        self.registers_view.configure(show="tree headings")
        self.registers_view.heading("#0", text="Register")
        self.registers_view.column("#0", anchor="center", width=100)

    def _build_menu(self) -> None:
        menu_bar = tk.Menu(self.root, tearoff=False)

        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_command(
            label="New Project",
            command=self.new_project,
            accelerator="Ctrl+N",
        )
        file_menu.add_command(
            label="Load Program",
            command=self.load_program,
            accelerator="Ctrl+L",
        )
        file_menu.add_command(
            label="Reset CPU",
            command=self.reset,
            accelerator="Ctrl+R",
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menu_bar.add_cascade(label="File", menu=file_menu)

        simulation_menu = tk.Menu(menu_bar, tearoff=False)
        simulation_menu.add_command(
            label="Step",
            command=self.step,
            accelerator="F10",
        )
        simulation_menu.add_command(
            label="Run",
            command=self.run,
            accelerator="F5",
        )
        simulation_menu.add_command(
            label="Stop",
            command=self.stop,
            accelerator="Shift+F5",
        )
        menu_bar.add_cascade(label="Simulation", menu=simulation_menu)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(
            label="About",
            command=lambda: messagebox.showinfo(
                "About",
                "AVR microcontroller simulator",
                parent=self.root,
            ),
        )
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.root.configure(menu=menu_bar)
        self.root.bind(
            "<Control-n>", lambda event: self._dispatch_shortcut(event, self.new_project)
        )
        self.root.bind(
            "<Control-l>", lambda event: self._dispatch_shortcut(event, self.load_program)
        )
        self.root.bind(
            "<Control-r>", lambda event: self._dispatch_shortcut(event, self.reset)
        )
        self.root.bind("<F10>", lambda event: self._dispatch_shortcut(event, self.step))
        self.root.bind("<F5>", lambda event: self._dispatch_shortcut(event, self.run))
        self.root.bind(
            "<Shift-F5>", lambda event: self._dispatch_shortcut(event, self.stop)
        )

    def _dispatch_shortcut(
        self, event: tk.Event, action: Callable[[], None]
    ) -> str:
        if event.widget.winfo_toplevel() is self.root:
            action()
        return "break"

    @staticmethod
    def _parse_program(text: str) -> bytearray:
        byte_values: list[int] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            source = line.split("#", maxsplit=1)[0].replace(",", " ")
            for token in source.split():
                normalized = token.removeprefix("0x").removeprefix("0X")
                try:
                    value = int(normalized, 16)
                except ValueError as error:
                    raise ValueError(
                        f"Invalid hex byte {token!r} on line {line_number}"
                    ) from error
                if not 0 <= value <= 0xFF:
                    raise ValueError(
                        f"Byte {token!r} on line {line_number} must be between 00 and FF"
                    )
                byte_values.append(value)

        if len(byte_values) % 2:
            raise ValueError("AVR program bytes must contain complete 2-byte instructions")
        return bytearray(byte_values)

    def load_program(self) -> None:
        try:
            program = self._parse_program(self.program_text.get("1.0", "end-1c"))
            new_cpu = self.cpu_factory()
            new_cpu.write_program(program)
        except (ValueError, MemoryError) as error:
            messagebox.showerror("Cannot load program", str(error), parent=self.root)
            return

        self.stop()
        self.program = program
        self.cpu = new_cpu
        self._refresh_registers()
        self._set_status(f"Loaded {len(program)} bytes.")

    def new_project(self) -> None:
        self.stop()
        self.program_text.delete("1.0", "end")
        self.program = bytearray()
        self.cpu = self.cpu_factory()
        self._refresh_registers()
        self._set_status("New empty project.")

    def step(self) -> None:
        self.stop()
        if not self.program:
            self._set_status("No program loaded.")
            return
        self._step_once()

    def _step_once(self) -> None:
        try:
            self.cpu.step()
        except (ValueError, IndexError, NotImplementedError) as error:
            self.stop()
            messagebox.showerror("Execution error", str(error), parent=self.root)
            self._set_status("Execution stopped due to an error.")
            return

        self._refresh_registers()
        if self.cpu.running:
            self._set_status("Running.")
        else:
            self._set_status("Stopped.")

    def run(self) -> None:
        if self.is_running:
            return
        if not self.program:
            self._set_status("No program loaded.")
            return
        self.is_running = True
        self.cpu.running = True
        self._set_status("Running.")
        self._run_next_instruction()

    def _run_next_instruction(self) -> None:
        if not self.is_running:
            return

        try:
            self.cpu.step()
        except (ValueError, IndexError, NotImplementedError) as error:
            self.stop()
            messagebox.showerror("Execution error", str(error), parent=self.root)
            self._set_status("Execution stopped due to an error.")
            return

        self._refresh_registers()
        if not self.cpu.running:
            self.is_running = False
            self._set_status("Program stopped.")
            return
        self.root.after(100, self._run_next_instruction)

    def stop(self) -> None:
        self.is_running = False
        self.cpu.running = False

    def reset(self) -> None:
        self.stop()
        self.cpu = self.cpu_factory()
        self.cpu.write_program(self.program)
        self._refresh_registers()
        self._set_status("CPU reset; program reloaded.")

    def _refresh_registers(self) -> None:
        self.pc_label.configure(text=f"PC: 0x{self.cpu.pc:04X}")
        for number in range(32):
            value = self.cpu.read_register(number)
            self.registers_view.item(
                str(number),
                values=(value, f"0x{value:02X}"),
            )

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)


def run_gui() -> None:
    root = tk.Tk()
    AVRSimulatorGUI(root)
    root.mainloop()
