import datetime
import random
from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QMessageBox, QHeaderView
from PyQt5.QtCore import QDate

import pyqtgraph as pg 
from PyQt5.uic import loadUi

from models.telemetry_model import TelemetryModel
from controllers.config_controller import ConfigController


class MainController(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("ui/main_window.ui", self)

        self.tableHistorico.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.model = TelemetryModel()
        
        self.x_data = []
        self.y_data = []
        self.plot_line = None
        
        self._setup_graph()

        self.dateEdit.blockSignals(True)
        self.dateEdit.setDate(QDate.currentDate())
        self.dateEdit.blockSignals(False)

        self._conectar_sinais()

    def _setup_graph(self):
        self.graphWidget.setBackground('w')
        self.graphWidget.setTitle("Histórico de Temperatura (°C)", color="#2C3E50", size="12pt")
        self.graphWidget.showGrid(x=True, y=True)

        self.x_data = []
        self.y_data = []
        
        self.plot_line = self.graphWidget.plot(
            self.x_data, 
            self.y_data, 
            pen=pg.mkPen(color='#E74C3C', width=2), 
            name="Temp (°C)"
        )

    def _conectar_sinais(self):
        self.btnConfig.clicked.connect(self.abrir_configuracoes)
        self.btnRegistrar.clicked.connect(self.simular_leitura)
        self.btnLimparTudo.clicked.connect(self.limpar_todo_historico)
        
        self.cbFiltro.currentIndexChanged.connect(self.aplicar_filtros)
        self.dateEdit.dateChanged.connect(self.aplicar_filtros)

    def calcular_ponto_orvalho(self, temp: float, umidade: float) -> float:
        """Calcula o Ponto de Orvalho aproximado usando a fórmula de Magnus-Tetens."""
        return round(temp - ((100.0 - umidade) / 5.0), 1)

    def atualizar_telemetria(self, temperatura: float, umidade: float, pressao: float):
        orvalho = self.calcular_ponto_orvalho(temperatura, umidade)
        status_ok = self.model.verificar_status_climatico(temperatura, umidade)

        self.lblTemperatura.setText(f"{temperatura:.1f} °C")
        self.lblUmidade.setText(f"{umidade:.0f} %")
        self.lblPressao.setText(f"{pressao:.1f} hPa")

        if temperatura > self.model.temp_max_alerta:
            status_txt = "ALERTA: CALOR EXTREMO"
            style = "background-color: #E74C3C; border-radius: 8px; padding: 10px; color: white;"
        elif temperatura < self.model.temp_min_alerta:
            status_txt = "ALERTA: FRIO INTENSO"
            style = "background-color: #3498DB; border-radius: 8px; padding: 10px; color: white;"
        elif umidade < self.model.umid_min_alerta:
            status_txt = "ALERTA: AR MUITO SECO"
            style = "background-color: #E67E22; border-radius: 8px; padding: 10px; color: white;"
        else:
            status_txt = "CLIMA ESTÁVEL (OK)"
            style = "background-color: #2ECC71; border-radius: 8px; padding: 10px; color: white;"

        self.lblStatusAlerta.setText(status_txt)
        self.cardAlerta.setStyleSheet(style)

        self.adicionar_tabela_historico(temperatura, umidade, pressao, orvalho, status_txt)
        
        novo_x = self.x_data[-1] + 1 if self.x_data else 1
        self.x_data.append(novo_x)
        self.y_data.append(temperatura)

        if self.plot_line:
            self.plot_line.setData(self.x_data, self.y_data)

    def adicionar_tabela_historico(self, temp, umid, press, orvalho, status):
        row = self.tableHistorico.rowCount()
        self.tableHistorico.insertRow(row)
        
        data_hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        dados = [
            data_hora, 
            f"{temp:.1f}", 
            f"{umid:.0f}", 
            f"{press:.1f}", 
            f"{orvalho:.1f}", 
            status
        ]
        
        for col, valor in enumerate(dados):
            self.tableHistorico.setItem(row, col, QTableWidgetItem(str(valor)))

        self.aplicar_filtros()

    def aplicar_filtros(self):
        """Oculta ou exibe as linhas da tabela de acordo com a opção e data selecionadas."""
        opcao_filtro = self.cbFiltro.currentText()
        data_filtro = self.dateEdit.date().toString("dd/MM/yyyy")

        for row in range(self.tableHistorico.rowCount()):
            item_data = self.tableHistorico.item(row, 0)
            item_temp = self.tableHistorico.item(row, 1)

            if not item_data or not item_temp:
                continue

            data_registro = item_data.text().split(" ")[0]
            try:
                temp_valor = float(item_temp.text())
            except ValueError:
                continue

            corresponde_data = (data_registro == data_filtro)

            corresponde_temp = True
            if opcao_filtro == "Temp. Alta (>30°C)":
                corresponde_temp = temp_valor > 30.0
            elif opcao_filtro == "Temp. Baixa (<15°C)":
                corresponde_temp = temp_valor < 15.0

            deve_exibir = corresponde_data and corresponde_temp
            self.tableHistorico.setRowHidden(row, not deve_exibir)

    def simular_leitura(self):
        temp_simulada = round(random.uniform(10.0, 40.0), 1)
        umid_simulada = random.randint(20, 95)
        press_simulada = round(random.uniform(1000.0, 1025.0), 1)

        if temp_simulada > self.model.temp_max_alerta:
            QMessageBox.warning(
                self, 
                "Alerta Climatológico", 
                f"Temperatura alta detectada: {temp_simulada}°C!\nAcima do limite de {self.model.temp_max_alerta}°C."
            )
        elif temp_simulada < self.model.temp_min_alerta:
            QMessageBox.warning(
                self, 
                "Alerta Climatológico", 
                f"Temperatura baixa detectada: {temp_simulada}°C!\nAbaixo do limite de {self.model.temp_min_alerta}°C."
            )

        self.atualizar_telemetria(temp_simulada, umid_simulada, press_simulada)

    def abrir_configuracoes(self):
        dialog = ConfigController(
            self.model.temp_max_alerta, 
            self.model.temp_min_alerta, 
            self.model.umid_min_alerta, 
            self
        )
        if dialog.exec_() == ConfigController.Accepted:
            temp_max, temp_min, umid_min = dialog.get_parametros()
            self.model.temp_max_alerta = temp_max
            self.model.temp_min_alerta = temp_min
            self.model.umid_min_alerta = umid_min
            
            QMessageBox.information(self, "Sucesso", "Novos parâmetros de alertas climáticos salvos!")
            self.atualizar_telemetria(temperatura=25.0, umidade=50, pressao=1013.2)

    def limpar_todo_historico(self):
        """Remove todas as linhas da tabela de histórico e reinicia o gráfico com botões customizados em PT-BR."""
        if self.tableHistorico.rowCount() == 0:
            QMessageBox.information(
                self, 
                "Informação", 
                "O histórico já está vazio."
            )
            return

        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("Confirmar Limpeza")
        msg_box.setText("Tem certeza que deseja apagar TODO o histórico de registros?")
        
        btn_sim = msg_box.addButton(QMessageBox.Yes)
        btn_nao = msg_box.addButton(QMessageBox.No)
        
        btn_sim.setText("Sim")
        btn_nao.setText("Não")
        
        msg_box.setDefaultButton(btn_nao)
        msg_box.exec_()

        if msg_box.clickedButton() == btn_sim:
            self.tableHistorico.setRowCount(0)
            
            self.x_data.clear()
            self.y_data.clear()
            if self.plot_line:
                self.plot_line.setData([], [])