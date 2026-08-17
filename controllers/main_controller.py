import datetime
import random
from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QMessageBox
from PyQt5.QtCore import QDate

import pyqtgraph as pg 
from PyQt5.uic import loadUi

from models.telemetry_model import TelemetryModel
from controllers.config_controller import ConfigController


class MainController(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("ui/main_window.ui", self)
        
        self.model = TelemetryModel()
        self.dateEdit.setDate(QDate.currentDate())
        
        self._setup_graph()
        self._conectar_sinais()
        
        # Leitura inicial padrão
        self.atualizar_telemetria(temperatura=24.5, umidade=65, pressao=1012.0)

    def _setup_graph(self):
        self.graphWidget.setBackground('w')
        self.graphWidget.setTitle("Histórico de Temperatura (°C)", color="#2C3E50", size="12pt")
        self.graphWidget.showGrid(x=True, y=True)
        
        horas, temps = self.model.gerar_dados_pre_carregados()
        self.graphWidget.plot(horas, temps, pen=pg.mkPen(color='#E74C3C', width=2), name="Temp (°C)")

    def _conectar_sinais(self):
        self.btnConfig.clicked.connect(self.abrir_configuracoes)
        self.btnRegistrar.clicked.connect(self.simular_leitura)

    def calcular_ponto_orvalho(self, temp: float, umidade: float) -> float:
        """Calcula o Ponto de Orvalho aproximado usando a fórmula de Magnus-Tetens."""
        return round(temp - ((100.0 - umidade) / 5.0), 1)

    def atualizar_telemetria(self, temperatura: float, umidade: float, pressao: float):
        orvalho = self.calcular_ponto_orvalho(temperatura, umidade)
        status_ok = self.model.verificar_status_climatico(temperatura, umidade)

        self.lblTemperatura.setText(f"{temperatura:.1f} °C")
        self.lblUmidade.setText(f"{umidade:.0f} %")
        self.lblPressao.setText(f"{pressao:.1f} hPa")

        # 2. Status Climático e Alerta Visual
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

        # 3. Adicionar registro na tabela
        self.adicionar_tabela_historico(temperatura, umidade, pressao, orvalho, status_txt)

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

    def simular_leitura(self):
        # Gera valores aleatórios coerentes com simulação de clima
        temp_simulada = round(random.uniform(10.0, 40.0), 1)
        umid_simulada = random.randint(20, 95)
        press_simulada = round(random.uniform(1000.0, 1025.0), 1)

        # Dispara aviso na tela se exceder os limites configurados
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