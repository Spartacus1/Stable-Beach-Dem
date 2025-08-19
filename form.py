# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(400, 600)
        
        # Main vertical layout
        self.mainLayout = QtWidgets.QVBoxLayout(Form)
        
        # Create tab widget
        self.tabWidget = QtWidgets.QTabWidget(Form)
        self.mainLayout.addWidget(self.tabWidget)
        
        # Tab 1 - Stable Beach Generation
        self.tab_beach = QtWidgets.QWidget()
        self.tabWidget.addTab(self.tab_beach, "Stable Beach Generation")
        self.beachLayout = QtWidgets.QVBoxLayout(self.tab_beach)
        
        # Add existing controls to first tab
        self.label = QtWidgets.QLabel("Select DEM Layer")
        self.beachLayout.addWidget(self.label)
        self.demLayerCombo = QtWidgets.QComboBox()
        self.beachLayout.addWidget(self.demLayerCombo)
        
        self.label_2 = QtWidgets.QLabel("Select Base Line (A)")
        self.beachLayout.addWidget(self.label_2)
        self.lineALayerCombo = QtWidgets.QComboBox()
        self.beachLayout.addWidget(self.lineALayerCombo)
        
        self.label_3 = QtWidgets.QLabel("Select Limit Line (B)")
        self.beachLayout.addWidget(self.label_3)
        self.lineBLayerCombo = QtWidgets.QComboBox()
        self.beachLayout.addWidget(self.lineBLayerCombo)
        
        self.label_4 = QtWidgets.QLabel("Enter Slope (degrees)")
        self.beachLayout.addWidget(self.label_4)
        self.slopeInput = QtWidgets.QLineEdit()
        self.beachLayout.addWidget(self.slopeInput)
        
        # Profile Creation Options Group
        self.profileOptionsGroup = QtWidgets.QGroupBox("Profile Creation Options")
        self.beachLayout.addWidget(self.profileOptionsGroup)
        self.optionsLayout = QtWidgets.QVBoxLayout(self.profileOptionsGroup)
        
        self.nodeBasedRadio = QtWidgets.QRadioButton("Node Based")
        self.nodeBasedRadio.setChecked(True)
        self.optionsLayout.addWidget(self.nodeBasedRadio)
        
        self.distanceIntervalRadio = QtWidgets.QRadioButton("Distance Interval")
        self.optionsLayout.addWidget(self.distanceIntervalRadio)
        
        self.distanceWidget = QtWidgets.QWidget()
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.distanceWidget)
        self.label_5 = QtWidgets.QLabel("Distance (m)")
        self.horizontalLayout.addWidget(self.label_5)
        self.distanceInput = QtWidgets.QLineEdit()
        self.distanceInput.setEnabled(False)
        self.horizontalLayout.addWidget(self.distanceInput)
        self.optionsLayout.addWidget(self.distanceWidget)
        
        # Interpolation Options
        self.interpolateCheckBox = QtWidgets.QCheckBox("Generate interpolated surface")
        self.beachLayout.addWidget(self.interpolateCheckBox)
        
        # Interpolation Parameters Group
        self.interpolationGroup = QtWidgets.QGroupBox("Interpolation Parameters")
        self.interpolationGroup.setVisible(False)
        self.beachLayout.addWidget(self.interpolationGroup)
        self.interpolationLayout = QtWidgets.QVBoxLayout(self.interpolationGroup)
        
        # Interpolation Mode
        self.modeWidget = QtWidgets.QWidget()
        self.modeLayout = QtWidgets.QHBoxLayout(self.modeWidget)
        self.modeLabel = QtWidgets.QLabel("Interpolation mode:")
        self.modeCombo = QtWidgets.QComboBox()
        self.modeCombo.addItems(['wmean', 'mean', 'median', 'mode'])
        self.modeLayout.addWidget(self.modeLabel)
        self.modeLayout.addWidget(self.modeCombo)
        self.interpolationLayout.addWidget(self.modeWidget)
        
        # Power parameter
        self.powerWidget = QtWidgets.QWidget()
        self.powerLayout = QtWidgets.QHBoxLayout(self.powerWidget)
        self.powerLabel = QtWidgets.QLabel("Power:")
        self.powerInput = QtWidgets.QLineEdit()
        self.powerInput.setText("2.0")
        self.powerLayout.addWidget(self.powerLabel)
        self.powerLayout.addWidget(self.powerInput)
        self.interpolationLayout.addWidget(self.powerWidget)
        
        # Number of cells parameter
        self.cellsWidget = QtWidgets.QWidget()
        self.cellsLayout = QtWidgets.QHBoxLayout(self.cellsWidget)
        self.cellsLabel = QtWidgets.QLabel("Number of cells to search:")
        self.cellsInput = QtWidgets.QLineEdit()
        self.cellsInput.setText("6")
        self.cellsLayout.addWidget(self.cellsLabel)
        self.cellsLayout.addWidget(self.cellsInput)
        self.interpolationLayout.addWidget(self.cellsWidget)
        
        # Search distance parameter
        self.distanceSearchWidget = QtWidgets.QWidget()
        self.distanceSearchLayout = QtWidgets.QHBoxLayout(self.distanceSearchWidget)
        self.distanceSearchLabel = QtWidgets.QLabel("Search distance (Max100):")
        self.distanceSearchInput = QtWidgets.QLineEdit()
        self.distanceSearchInput.setText("0.5")
        self.distanceSearchLayout.addWidget(self.distanceSearchLabel)
        self.distanceSearchLayout.addWidget(self.distanceSearchInput)
        self.interpolationLayout.addWidget(self.distanceSearchWidget)
        
        # No nulls option
        self.noNullsCheckBox = QtWidgets.QCheckBox("Do not propagate null values")
        self.noNullsCheckBox.setChecked(True)
        self.interpolationLayout.addWidget(self.noNullsCheckBox)
        
        # Spacer for first tab
        spacerBeach = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.beachLayout.addItem(spacerBeach)
        
        # Tab 2 - Volume Calculation Grid
        self.tab_volume = QtWidgets.QWidget()
        self.tabWidget.addTab(self.tab_volume, "Volume Calculation Grid")
        self.volumeLayout = QtWidgets.QVBoxLayout(self.tab_volume)
        
        # Add controls for volume calculation
        self.polyLabel = QtWidgets.QLabel("Select Polygon Layer")
        self.volumeLayout.addWidget(self.polyLabel)
        self.polygonLayerCombo = QtWidgets.QComboBox()
        self.volumeLayout.addWidget(self.polygonLayerCombo)
        
        self.gridSizeLabel = QtWidgets.QLabel("Grid Cell Size")
        self.volumeLayout.addWidget(self.gridSizeLabel)
        self.gridSizeInput = QtWidgets.QLineEdit()
        self.volumeLayout.addWidget(self.gridSizeInput)

        # Add overlap checkbox
        self.overlapCheckBox = QtWidgets.QCheckBox("Only Generate Overlap Cells")
        self.volumeLayout.addWidget(self.overlapCheckBox)

        # Add Generate Grid button
        self.generateGridButton = QtWidgets.QPushButton("Generate Grid")
        self.volumeLayout.addWidget(self.generateGridButton)
        
        # Spacer for second tab
        spacerVolume = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.volumeLayout.addItem(spacerVolume)
        
        # Run button (outside tabs)
        self.runButton = QtWidgets.QPushButton("Generate")
        self.mainLayout.addWidget(self.runButton)
        
        # Progress bar and status label (outside tabs)
        self.statusLabel = QtWidgets.QLabel("Ready")
        self.mainLayout.addWidget(self.statusLabel)
        
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setValue(0)
        self.mainLayout.addWidget(self.progressBar)
        
        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)
        
        # Connect signals
        self.nodeBasedRadio.toggled.connect(self.onProfileOptionChanged)
        self.distanceIntervalRadio.toggled.connect(self.onProfileOptionChanged)
        self.interpolateCheckBox.toggled.connect(self.interpolationGroup.setVisible)
        
    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Beach Analysis Tool"))
        
    def onProfileOptionChanged(self):
        self.distanceInput.setEnabled(self.distanceIntervalRadio.isChecked())