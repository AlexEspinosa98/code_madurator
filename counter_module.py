
from PyQt6.QtWidgets import QMessageBox

class Counter:
    """
    Contador con límites, mensajes y soporte de setpoint.
    """
    def __init__(self, name, min_value=0, max_value=None, message="¡Valor fuera de rango!", parent=None, initial_value: int = 0):
        self.name = name
        self.min_value = min_value
        self.max_value = max_value
        self.value = initial_value
        self.setpoint = initial_value
        self.message = message
        self.parent = parent

    def change(self, delta):
        self.value += delta
        self._validate()

    def set_current(self):
        """
        Guarda el valor actual en el setpoint.
        """
        self.setpoint = self.value

    def reset_to_setpoint(self):
        """
        Carga el setpoint al value.
        """
        self.value = self.setpoint
        self._validate()

    def _validate(self):
        """
        Valida límites y muestra mensajes si corresponde.
        """
        if self.value < self.min_value:
            QMessageBox.critical(
                self.parent,
                "Emergencia",
                f"{self.message}\n(Mínimo permitido: {self.min_value})"
            )
            self.value = self.min_value

        if self.max_value is not None and self.value > self.max_value:
            QMessageBox.critical(
                self.parent,
                "Emergencia",
                f"{self.message}\n(Máximo permitido: {self.max_value})"
            )
            self.value = self.max_value

