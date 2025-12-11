# -*- coding: utf-8 -*-
import os
import sys
import clr
import System
from pyrevit import forms, script
from manalib import auth

# URL do Frontend para registro
REGISTER_URL = "https://front-end-mana-tools.vercel.app/"

class LoginWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        # Inicializa UI
        self.update_ui()

    def update_ui(self):
        # Verifica estado atual
        info = auth.get_license_info()
        
        if info["email"] != "Desconectado":
            # Logado
            self.panel_login.Visibility = System.Windows.Visibility.Collapsed
            self.panel_info.Visibility = System.Windows.Visibility.Visible
            
            self.txt_user_email.Text = info["email"]
            self.txt_license_status.Text = info["status"]
            
            if info["is_valid"]:
                self.txt_license_status.Foreground = System.Windows.Media.Brushes.Green
            else:
                self.txt_license_status.Foreground = System.Windows.Media.Brushes.Red
        else:
            # Deslogado
            self.panel_login.Visibility = System.Windows.Visibility.Visible
            self.panel_info.Visibility = System.Windows.Visibility.Collapsed
            self.tb_email.Text = ""
            self.pb_password.Password = ""
            self.lbl_status.Text = ""

    # Evento do Botão Login (Definido no XAML)
    def button_login_clicked(self, sender, args):
        email = self.tb_email.Text
        pwd = self.pb_password.Password
        
        if not email or not pwd:
            self.lbl_status.Text = "Preencha e-mail e senha."
            return

        self.lbl_status.Text = "Autenticando..."
        
        # Força refresh visual antes de travar na requisição
        System.Windows.Threading.Dispatcher.CurrentDispatcher.Invoke(lambda: None, System.Windows.Threading.DispatcherPriority.Background)
        
        # Chama Auth
        success, msg = auth.login(email, pwd)
        
        if success:
            self.update_ui()
        else:
            self.lbl_status.Text = msg

    # Evento do Botão Logout (Definido no XAML)
    def button_logout_clicked(self, sender, args):
        try:
            auth.logout()
            self.update_ui()
        except Exception as e:
            forms.alert("Erro ao sair: {}".format(e))

    # Evento do Link Registro
    def link_register_clicked(self, sender, args):
        try:
            System.Diagnostics.Process.Start(REGISTER_URL)
        except: pass

# Instancia e Mostra
win = LoginWindow()
win.ShowDialog()