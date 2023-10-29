import sys

from PyQt6.QtWidgets import QApplication, QTableView
from mapping_model import MappingModel

# Assuming you already have a mapping that you want to display
my_mapping = {"key1": "value1", "key2": "value2", "key3": "value3"}


# Create an instance of the MappingModel
model = MappingModel[str, str]()

# Set the mapping to be displayed by the model
model.set_mapping(my_mapping)

# Create a QTableView and set the model
app = QApplication(sys.argv)
table_view = QTableView()
table_view.setModel(model)

# Show the table view
table_view.show()
sys.exit(app.exec())
