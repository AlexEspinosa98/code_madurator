from PyQt6.QtWidgets import QApplication, QMainWindow
import sys
from generator_code import Ui_Generator  # Cambia según la clase generada

class MainWindow(QMainWindow):
	def __init__(self):
		print("por aca pse1")
		super(MainWindow, self).__init__()
		print("por aca pse5")
		self.ui = Ui_Generator()  # Cambia si la clase generada es diferente
		print("por aca pse6")
		self.ui.setupUi(self)


print("por aca pse2")
app = QApplication(sys.argv)
print("por aca pse3")
window = MainWindow()
print("por aca pse4")
window.show()
sys.exit(app.exec())
