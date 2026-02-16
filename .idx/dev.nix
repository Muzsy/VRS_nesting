# To learn more about how to use Nix to configure your environment
# see: https://developers.google.com/idx/guides/customize-idx-env
{ pkgs, ... }: {
  # Melyik csatornát használjuk (a 24.05 a stabil, 2026-os alap)
  channel = "stable-24.05";

  # Itt adhatod meg a terminálban elérhető csomagokat
  packages = [
    # --- Python Környezet ---
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.pytest
    pkgs.python311Packages.virtualenv

    # --- YAML és Adatkezelés ---
    pkgs.yq-go            # Parancssoros YAML feldolgozó (szuper a tervedhez!)
    pkgs.jq               # JSON feldolgozó

    # --- Fejlesztői Eszközök ---
    pkgs.gh               # GitHub CLI
    pkgs.git
    pkgs.htop             # Rendszererőforrás figyelő
    pkgs.curl
    pkgs.wget
  ];

  # Környezeti változók beállítása
  env = {
    PYTHONPATH = "./src";
    # Megkönnyíti a Gemini dolgát, hogy tudja, mi a projekt alapnyelve
    PROJECT_TYPE = "python-yaml-agent";
  };

  idx = {
    # Itt adhatod meg a VS Code extensionöket
    extensions = [
      "ms-python.python"            # Python támogatás
      "ms-python.vscode-pylance"     # Okos kódkiegészítés
      "redhat.vscode-yaml"          # YAML támogatás és validálás
      "google.gemini-code-assist"   # Maga a Gemini (ha nem lenne alapból aktív)
      "tamasfe.even-better-toml"    # Ha használnál TOML-t is
    ];

    # Események, amik a környezet felállásakor fussanak le
    workspace = {
      # Egyszer fut le a projekt létrehozásakor
      onCreate = {
        # Virtuális környezet létrehozása és alap csomagok telepítése
        setup-venv = "python -m venv .venv && source .venv/bin/activate && pip install --upgrade pip";
        # Ha van requirements.txt, automatikusan telepíti
        install-deps = "if [ -f requirements.txt ]; then pip install -r requirements.txt; fi";
      };
      
      # Minden alkalommal lefut, amikor megnyitod az IDX-et
      onStart = {
        # Aktiválja a venv-et automatikusan
        activate-venv = "source .venv/bin/activate";
      };
    };

    # Ha webes appot fejlesztenél, itt láthatnád az előnézetet
    previews = {
      enable = true;
      previews = {
        # web = {
        #   command = ["python3" "-m" "http.server" "$PORT"];
        #   manager = "web";
        # };
      };
    };
  };
}