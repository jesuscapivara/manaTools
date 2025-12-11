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
Source: "ManaTools.extension\*"; DestDir: "{commonappdata}\pyRevit\Extensions\ManaTools.extension"; Flags: ignoreversion recursesubdirs createallsubdirs

[Code]
var
  PyRevitInstalledPage: TOutputMsgWizardPage;

// Verifica se pyRevit está instalado
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
  
  // Verifica paths comuns
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
  
  Result := False;
end;

// Cria página de aviso se pyRevit não estiver instalado
procedure InitializeWizard;
begin
  if not IsPyRevitInstalled() then
  begin
    PyRevitInstalledPage := CreateOutputMsgPage(wpWelcome,
      'pyRevit não encontrado',
      'O pyRevit é necessário para usar o ManaTools',
      'O instalador não detectou o pyRevit instalado neste computador. ' +
      'O ManaTools é uma extensão do pyRevit e requer que ele esteja instalado.' + #13#10#13#10 +
      'Por favor, instale o pyRevit antes de continuar:' + #13#10 +
      'https://github.com/pyrevitlabs/pyRevit/releases' + #13#10#13#10 +
      'Após instalar o pyRevit, execute este instalador novamente.');
  end;
end;

// Bloqueia instalação se pyRevit não estiver presente
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  
  if (CurPageID = wpWelcome) and (not IsPyRevitInstalled()) then
  begin
    Result := False;
    MsgBox('Por favor, instale o pyRevit antes de prosseguir com a instalação do ManaTools.', mbError, MB_OK);
  end;
end;

[Run]
; Mensagem pós-instalação
Filename: "{cmd}"; Parameters: "/c echo ManaTools instalado com sucesso! & echo. & echo Reinicie o Revit para carregar a extensão. & pause"; Flags: runhidden waituntilterminated postinstall skipifsilent; Description: "Ver instruções finais"

[UninstallDelete]
; Remove toda a pasta da extensão na desinstalação
Type: filesandordirs; Name: "{commonappdata}\pyRevit\Extensions\ManaTools.extension"

[Messages]
brazilianportuguese.WelcomeLabel2=Este assistente instalará o [name/ver] no seu computador.%n%nO ManaTools é uma extensão para pyRevit/Revit focada em fluxos BIM ágeis.%n%nRecomenda-se fechar o Revit antes de continuar.
brazilianportuguese.FinishedHeadingLabel=Instalação concluída com sucesso
brazilianportuguese.FinishedLabelNoIcons=O ManaTools foi instalado. Reinicie o Revit para carregar a extensão.

