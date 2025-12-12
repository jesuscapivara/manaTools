; Script de Instalação Inno Setup para ManaTools
; Gera um instalador EXE profissional para extensão pyRevit

#define MyAppName "ManaTools"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Lucas Rossetti"
#define MyAppURL "https://www.manatools.com.br"

[Setup]
; Informações do App
AppId={{8F3A2B1C-9D4E-4F5A-8B2C-1E6D7F9A3C5B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Configurações de Instalação
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=.\dist
OutputBaseFilename=ManaToolsSetup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

; Requisitos
PrivilegesRequired=admin
MinVersion=6.1

; Ícones (adicione um icon.ico na raiz se tiver)
; SetupIconFile=icon.ico
; UninstallDisplayIcon={app}\icon.ico

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
; Copia toda a extensão para o diretório de extensões do pyRevit
; O caminho será determinado automaticamente (Admin ou User)
Source: "ManaTools.extension\*"; DestDir: "{code:GetPyRevitExtensionsPath}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Script PowerShell para registro (temporário)
Source: "registrar_extensao_instalador.ps1"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Code]
var
  PyRevitExtensionsPath: String;

// Determina automaticamente onde o pyRevit está instalado
function GetPyRevitExtensionsPath(Param: String): String;
var
  UserPath, AdminPath: String;
begin
  // Caminho de instalação do usuário (AppData)
  UserPath := ExpandConstant('{userappdata}\pyRevit\Extensions');
  // Caminho de instalação admin (ProgramData)
  AdminPath := ExpandConstant('{commonappdata}\pyRevit\Extensions');
  
  // Verifica qual existe e prioriza o que tem arquivos
  if DirExists(UserPath) then
  begin
    Result := UserPath + '\ManaTools.extension';
    PyRevitExtensionsPath := UserPath;
    Log('pyRevit detectado (User): ' + UserPath);
  end
  else if DirExists(AdminPath) then
  begin
    Result := AdminPath + '\ManaTools.extension';
    PyRevitExtensionsPath := AdminPath;
    Log('pyRevit detectado (Admin): ' + AdminPath);
  end
  else
  begin
    // Padrão: Admin
    Result := AdminPath + '\ManaTools.extension';
    PyRevitExtensionsPath := AdminPath;
    Log('pyRevit não encontrado, usando padrão (Admin): ' + AdminPath);
  end;
end;

procedure LogInstallPath();
begin
  Log('Arquivos serão instalados em: ' + PyRevitExtensionsPath);
end;

// Registra a extensão no arquivo de configuração do pyRevit usando PowerShell
// PowerShell garante UTF-8 correto e evita corrupção do arquivo
procedure RegisterExtensionInPyRevit();
var
  ResultCode: Integer;
  PowerShellScript: String;
  PowerShellArgs: String;
begin
  Log('Registrando extensao no pyRevit via PowerShell...');
  Log('Extension path: ' + PyRevitExtensionsPath);
  
  // Caminho do script PowerShell (copiado para {tmp})
  PowerShellScript := ExpandConstant('{tmp}\registrar_extensao_instalador.ps1');
  
  // Argumentos para o PowerShell
  PowerShellArgs := '-NoProfile -ExecutionPolicy Bypass -File "' + PowerShellScript + '" -ExtensionPath "' + PyRevitExtensionsPath + '"';
  
  Log('Executando PowerShell com: ' + PowerShellArgs);
  
  // Executa o script
  if Exec('powershell.exe', PowerShellArgs, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
      Log('Extensao registrada com sucesso!')
    else
      Log('PowerShell retornou codigo: ' + IntToStr(ResultCode));
  end
  else
  begin
    Log('Erro ao executar PowerShell');
  end;
end;

// Verifica se pyRevit está instalado (Admin ou User)
function IsPyRevitInstalled(): Boolean;
var
  PyRevitPath: String;
begin
  // Verifica registro
  if RegQueryStringValue(HKLM, 'SOFTWARE\pyRevit', 'InstallPath', PyRevitPath) then
  begin
    Result := DirExists(PyRevitPath);
    Exit;
  end;
  
  // Verifica paths comuns (Admin)
  if DirExists('C:\Program Files\pyRevit-Master') then
  begin
    Result := True;
    Exit;
  end;
  
  if DirExists(ExpandConstant('{commonappdata}\pyRevit')) then
  begin
    Result := True;
    Exit;
  end;
  
  // Verifica instalação local do usuário (User)
  if DirExists(ExpandConstant('{userappdata}\pyRevit')) then
  begin
    Result := True;
    Exit;
  end;
  
  if DirExists(ExpandConstant('{localappdata}\pyRevit')) then
  begin
    Result := True;
    Exit;
  end;
  
  Result := False;
end;

// Cria página de aviso se pyRevit não estiver instalado
procedure InitializeWizard;
begin
  // Verificação movida para NextButtonClick para evitar loop
end;

// Abre o link do pyRevit no navegador
procedure OpenPyRevitDownloadPage();
var
  ErrorCode: Integer;
begin
  ShellExec('open', 'https://github.com/pyrevitlabs/pyRevit/releases', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
end;

// Bloqueia instalação se pyRevit não estiver presente
function NextButtonClick(CurPageID: Integer): Boolean;
var
  Response: Integer;
begin
  Result := True;
  
  if (CurPageID = wpWelcome) and (not IsPyRevitInstalled()) then
  begin
    Response := MsgBox(
      'O pyRevit não foi encontrado neste computador.' + #13#10#13#10 +
      'O ManaTools requer o pyRevit para funcionar.' + #13#10#13#10 +
      'Deseja abrir a página de download do pyRevit agora?' + #13#10#13#10 +
      'https://github.com/pyrevitlabs/pyRevit/releases' + #13#10#13#10 +
      'A instalação será CANCELADA após esta mensagem.',
      mbConfirmation, MB_YESNO
    );
    
    if Response = IDYES then
    begin
      OpenPyRevitDownloadPage();
    end;
    
    // SEMPRE fecha o instalador após mostrar a mensagem
    Result := False;
    WizardForm.Close;
  end;
end;

// Registra extensão após instalação dos arquivos
procedure CurStepChanged(CurStep: TSetupStep);
var
  UserConfigPath, AdminConfigPath, ConfigPath: String;
  ConfigExists: Boolean;
begin
  if CurStep = ssPostInstall then
  begin
    Log('Pós-instalação: Verificando pyRevit_config.ini...');
    
    // Verifica se o arquivo de config existe
    UserConfigPath := ExpandConstant('{userappdata}\pyRevit\pyRevit_config.ini');
    AdminConfigPath := ExpandConstant('{commonappdata}\pyRevit\pyRevit_config.ini');
    
    ConfigExists := FileExists(UserConfigPath) or FileExists(AdminConfigPath);
    
    if ConfigExists then
    begin
      Log('Config encontrado. Registrando extensão...');
      RegisterExtensionInPyRevit();
    end
    else
    begin
      Log('AVISO: pyRevit_config.ini não existe ainda.');
      Log('O usuário precisa abrir o Revit/pyRevit uma vez primeiro.');
      
      MsgBox(
        'IMPORTANTE:' + #13#10#13#10 +
        'O ManaTools foi instalado, mas o pyRevit ainda não foi executado.' + #13#10#13#10 +
        'Para concluir a configuração:' + #13#10 +
        '1. Abra o Revit (o pyRevit criará os arquivos necessários)' + #13#10 +
        '2. Feche o Revit' + #13#10 +
        '3. Execute este instalador novamente para registrar a extensão' + #13#10#13#10 +
        'OU' + #13#10#13#10 +
        'No Revit, clique no ícone pyRevit > Settings > Extensions > Add Folder e selecione:' + #13#10 +
        PyRevitExtensionsPath,
        mbInformation, MB_OK
      );
    end;
  end;
end;

[UninstallDelete]
; Remove toda a pasta da extensão na desinstalação (ambos os caminhos possíveis)
Type: filesandordirs; Name: "{commonappdata}\pyRevit\Extensions\ManaTools.extension"
Type: filesandordirs; Name: "{userappdata}\pyRevit\Extensions\ManaTools.extension"

[Messages]
brazilianportuguese.WelcomeLabel2=Este assistente instalará o [name/ver] no seu computador.%n%nO ManaTools é uma extensão para pyRevit/Revit focada em fluxos BIM ágeis.%n%nREQUISITO: pyRevit 5.0 ou superior instalado%n(https://github.com/pyrevitlabs/pyRevit/releases)%n%nRecomenda-se fechar o Revit antes de continuar.
brazilianportuguese.FinishedHeadingLabel=Instalação concluída com sucesso!
brazilianportuguese.FinishedLabelNoIcons=O ManaTools foi instalado e configurado automaticamente.%n%nA extensão será carregada no seu pyRevit.%n%nPRÓXIMOS PASSOS:%n1. Abra o Revit%n2. A aba ManaTools aparecerá automaticamente%n%nSe não aparecer, clique no ícone pyRevit e escolha "Reload".

