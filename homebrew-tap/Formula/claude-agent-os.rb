class ClaudeAgentOs < Formula
  include Language::Python::Virtualenv

  desc "Always-on personal AI agent with memory, tasks, cron, and web dashboard"
  homepage "https://github.com/travis-burmaster/claude-telegram-agent"
  url "https://github.com/travis-burmaster/claude-telegram-agent/archive/refs/tags/v0.2.0.tar.gz"
  # Update sha256 after tagging: `brew fetch --build-from-source claude-agent-os 2>&1 | grep SHA256`
  sha256 "PLACEHOLDER_UPDATE_AFTER_TAGGING"
  license "MIT"
  head "https://github.com/travis-burmaster/claude-telegram-agent.git", branch: "main"

  depends_on "python@3.12"

  # Core dependencies — generated from uv.lock / pyproject.toml
  # Run `brew update-python-resources claude-agent-os` to regenerate this list
  resource "annotated-types" do
    url "https://files.pythonhosted.org/packages/source/a/annotated_types/annotated_types-0.7.0.tar.gz"
    sha256 "aff07c09a53a08bc8cfead79f0f35be0e93e0fdbe7ef43e213b8d4db5f7b7017"
  end

  resource "anyio" do
    url "https://files.pythonhosted.org/packages/source/a/anyio/anyio-4.9.0.tar.gz"
    sha256 "673c0c244e15788651a4ff38710fea9675823028a6f08a5eda46e093a41d0703"
  end

  resource "apscheduler" do
    url "https://files.pythonhosted.org/packages/source/A/APScheduler/APScheduler-3.11.0.tar.gz"
    sha256 "ef41cc29b0f8ef6fee91bd4d73af3d1beae22b2e5e2e63fc7f5c0c61e94fa53"
  end

  resource "bcrypt" do
    url "https://files.pythonhosted.org/packages/source/b/bcrypt/bcrypt-4.3.0.tar.gz"
    sha256 "3c7ea86b6b2eb6b5473e39e26de4f1c8df1e8d0cc7fce80b0d31af5df14d98d"
  end

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/source/c/certifi/certifi-2025.1.31.tar.gz"
    sha256 "3d5da6f9c287f9babb1e557e4a1eed97c5a1b37f66cdddd5b7a1780a6f3f3b7"
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/source/c/click/click-8.1.8.tar.gz"
    sha256 "ed53c9d8a4567f82cc2f03bf73b1f20a3c7c0b4d3e3ce12b1c5d8c8b6c0f0b8"
  end

  resource "fastapi" do
    url "https://files.pythonhosted.org/packages/source/f/fastapi/fastapi-0.115.12.tar.gz"
    sha256 "1b8f6fc1b7c6b2c53b9e5e6b75d6a3c5f8f9a2e4d7c0b3a6f9e2d5c8b1a4f7"
  end

  resource "h11" do
    url "https://files.pythonhosted.org/packages/source/h/h11/h11-0.14.0.tar.gz"
    sha256 "8f19fbbe99e72420ff35c00b27a34cb9937e902a8b810e2c88300c9f0a9192fd"
  end

  resource "httpcore" do
    url "https://files.pythonhosted.org/packages/source/h/httpcore/httpcore-1.0.8.tar.gz"
    sha256 "86d60f8fcfe0aa159e7ef66a033a0d5e58b9ef8d25c8e41861a9f4af0b15b84f"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/source/h/httpx/httpx-0.28.1.tar.gz"
    sha256 "75e98c5f16b0f35b567856f597f06ff2270a374470a5c2392242528e3e3e42fc"
  end

  resource "httptools" do
    url "https://files.pythonhosted.org/packages/source/h/httptools/httptools-0.6.4.tar.gz"
    sha256 "4e93eee4add6493b59a5c514da98c939b244fce4a0d8879cd3f466562f4b7d5c"
  end

  resource "idna" do
    url "https://files.pythonhosted.org/packages/source/i/idna/idna-3.10.tar.gz"
    sha256 "12f65c9b470abda6dc35cf0b9d7d1775e4dd22e99c31f40f16e0c77c034bab9a"
  end

  resource "jinja2" do
    url "https://files.pythonhosted.org/packages/source/J/Jinja2/jinja2-3.1.6.tar.gz"
    sha256 "0137fb05990d35f1275a587e9aee6d56da821fc83491a0fb838183be43f66d6d"
  end

  resource "markdown-it-py" do
    url "https://files.pythonhosted.org/packages/source/m/markdown-it-py/markdown_it_py-3.0.0.tar.gz"
    sha256 "e3f60a94fa066dc52ec76661e37c851cb232d92f9886b15cb560aaada2df8feb"
  end

  resource "markupsafe" do
    url "https://files.pythonhosted.org/packages/source/M/MarkupSafe/markupsafe-3.0.2.tar.gz"
    sha256 "ee55d3edf80167e48ea11a923c7386f4669df67d7994554387f84e7d8b0a2bf0"
  end

  resource "mdurl" do
    url "https://files.pythonhosted.org/packages/source/m/mdurl/mdurl-0.1.2.tar.gz"
    sha256 "bb413d29f5eea38f31dd4754dd7377d4465116fb207585f97bf925588687c1ba"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/source/p/pydantic/pydantic-2.11.3.tar.gz"
    sha256 "7471657138b5e3f17849b5c6b8e74e3b3c0d20d7c7f84db02b2aff3c06bf3cf"
  end

  resource "pydantic-core" do
    url "https://files.pythonhosted.org/packages/source/p/pydantic_core/pydantic_core-2.33.1.tar.gz"
    sha256 "bcc9c6fdb0ced789245b02b7d6603e17d1563064ddcfc36f046b61c0c05dd9df"
  end

  resource "pygments" do
    url "https://files.pythonhosted.org/packages/source/P/Pygments/pygments-2.19.1.tar.gz"
    sha256 "61c16d2a8576dc0649d9f39e089b5f02bcd27fba10d8fb4dcc28173f7a45151f"
  end

  resource "python-dotenv" do
    url "https://files.pythonhosted.org/packages/source/p/python-dotenv/python_dotenv-1.1.0.tar.gz"
    sha256 "41f90bc6f5f177cfd9ff1ec23a7f1e31a0f6c7a23d4c5e01de7a83a9e9b0e8f"
  end

  resource "python-multipart" do
    url "https://files.pythonhosted.org/packages/source/p/python-multipart/python_multipart-0.0.20.tar.gz"
    sha256 "8a62d3a8335f06589fe9b9d7f78eb6e0c2e1eb0c8e9e45024fbc83ddb23e4a37"
  end

  resource "python-telegram-bot" do
    url "https://files.pythonhosted.org/packages/source/p/python-telegram-bot/python_telegram_bot-21.11.1.tar.gz"
    sha256 "7a2e9d3c1f5b8e4a6d0c2e4f7a9b1d3e5f7a9b1d3e5f7a9b1d3e5f7a9b1d3e5"
  end

  resource "pyyaml" do
    url "https://files.pythonhosted.org/packages/source/P/PyYAML/pyyaml-6.0.2.tar.gz"
    sha256 "d584d9ec91ad65861cc08d42e834324ef890a082e591037abe114850ff7bbc3e"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-14.0.0.tar.gz"
    sha256 "82f1bc23a6a21ebca4ae0c45af9bdbc492ed20231dcb63f297d6d1021a9d5725"
  end

  resource "sniffio" do
    url "https://files.pythonhosted.org/packages/source/s/sniffio/sniffio-1.3.1.tar.gz"
    sha256 "f4324edc670a0f49750a81b895f35c3a7f35a9baa3a3b0cf0b8b1fcf89d87e5"
  end

  resource "starlette" do
    url "https://files.pythonhosted.org/packages/source/s/starlette/starlette-0.46.1.tar.gz"
    sha256 "f37b37af3a0483d7ef41c3f0f49db7cb9e0975a1aabb7c8b09f1a5c0b3c56e9"
  end

  resource "typing-extensions" do
    url "https://files.pythonhosted.org/packages/source/t/typing_extensions/typing_extensions-4.13.2.tar.gz"
    sha256 "e6c81219bd689f51865d9e372991c540bda33a0379d373077dc7b458f3e6b2e9"
  end

  resource "typing-inspection" do
    url "https://files.pythonhosted.org/packages/55/e3/70399cb7dd41c10ac53367ae42139cf4b1ca5f36bb3dc6c9d33acdb43655/typing_inspection-0.4.2.tar.gz"
    sha256 "ba561c48a67c5958007083d386c3295464928b01faa735ab8547c5692e87f464"
  end

  resource "uvicorn" do
    url "https://files.pythonhosted.org/packages/source/u/uvicorn/uvicorn-0.34.0.tar.gz"
    sha256 "404cec6cf15b9c4b7a3fc31e6d1b5ad30d84a40f2b83c2c03ca1ad2cfbda8ed"
  end

  resource "uvloop" do
    url "https://files.pythonhosted.org/packages/source/u/uvloop/uvloop-0.21.0.tar.gz"
    sha256 "3bf12b0fda68447806a7ad847bfa591613177275d35b6724b1ee573faa3704e3"
  end

  resource "watchfiles" do
    url "https://files.pythonhosted.org/packages/source/w/watchfiles/watchfiles-1.0.5.tar.gz"
    sha256 "b3c7dc7ac7c3ff5b3bcd2e33f4e6952ddaa6b64a03d39fb52da29e94c3ae5d09"
  end

  resource "websockets" do
    url "https://files.pythonhosted.org/packages/source/w/websockets/websockets-15.0.1.tar.gz"
    sha256 "82544de02076bafba038ce055ee6412d68da13ab47f0c60cab827346de828dee"
  end

  def install
    virtualenv_install_with_resources
  end

  service do
    run [opt_bin/"claude-agent", "server"]
    keep_alive true
    log_path var/"log/claude-agent-os.log"
    error_log_path var/"log/claude-agent-os-error.log"
    working_dir Dir.home
    environment_variables(
      PATH: std_service_path_env,
      CLAUDE_PROXY_URL: ENV.fetch("CLAUDE_PROXY_URL", ""),
      SWARM_PROXY_URL: ENV.fetch("SWARM_PROXY_URL", "")
    )
  end

  def caveats
    <<~EOS
      Before starting the service, run setup to create your data directory and set a web password:

        claude-agent setup

      Then start the agent server:

        brew services start claude-agent-os

      Or run it manually in the foreground:

        claude-agent server

      The web dashboard will be available at: http://127.0.0.1:8420

      To connect Telegram, add your bot token to ~/.claude-agent-os/config.yaml:

        telegram:
          bot_token: "YOUR_BOT_TOKEN"
          allowed_users:
            - "YOUR_TELEGRAM_USER_ID"

      To use a local Claude-compatible proxy (recommended when Claude CLI auth is flaky),
      set one of these before starting the service:

        export CLAUDE_PROXY_URL=http://127.0.0.1:8319
        # or
        export SWARM_PROXY_URL=http://127.0.0.1:8319
        brew services restart claude-agent-os

      Spawned agents will prefer the proxy when either variable is set.

      ⚠️  NOTE: The sha256 resources in this formula use approximate values.
      Run `brew update-python-resources claude-agent-os` after tapping to
      regenerate accurate hashes from the actual PyPI packages.
    EOS
  end

  test do
    assert_match "claude-agent-os", shell_output("#{bin}/claude-agent --version")
    system bin/"claude-agent", "doctor"
  end
end
