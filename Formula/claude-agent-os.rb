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
  depends_on "rust" => :build

  # Core dependencies — generated from uv.lock / pyproject.toml
  # Run `brew update-python-resources claude-agent-os` to regenerate this list
  resource "annotated-types" do
    url "https://files.pythonhosted.org/packages/source/a/annotated_types/annotated_types-0.7.0.tar.gz"
    sha256 "aff07c09a53a08bc8cfccb9c85b05f1aa9a2a6f23728d790723543408344ce89"
  end

  resource "anyio" do
    url "https://files.pythonhosted.org/packages/source/a/anyio/anyio-4.9.0.tar.gz"
    sha256 "673c0c244e15788651a4ff38710fea9675823028a6f08a5eda409e0c9840a028"
  end

  resource "apscheduler" do
    url "https://files.pythonhosted.org/packages/source/A/APScheduler/apscheduler-3.11.2.tar.gz"
    sha256 "2a9966b052ec805f020c8c4c3ae6e6a06e24b1bf19f2e11d91d8cca0473eef41"
  end

  resource "bcrypt" do
    url "https://files.pythonhosted.org/packages/source/b/bcrypt/bcrypt-4.3.0.tar.gz"
    sha256 "3a3fd2204178b6d2adcf09cb4f6426ffef54762577a7c9b54c159008cb288c18"
  end

  resource "cffi" do
    url "https://files.pythonhosted.org/packages/eb/56/b1ba7935a17738ae8453301356628e8147c79dbb825bcbc73dc7401f9846/cffi-2.0.0.tar.gz"
    sha256 "44d1b5909021139fe36001ae048dbdde8214afa20200eda0f64c068cac5d5529"
  end

  resource "certifi" do
    url "https://files.pythonhosted.org/packages/source/c/certifi/certifi-2025.1.31.tar.gz"
    sha256 "3d5da6925056f6f18f119200434a4780a94263f10d1c21d032a6f6b2baa20651"
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/source/c/click/click-8.1.8.tar.gz"
    sha256 "ed53c9d8990d83c2a27deae68e4ee337473f6330c040a31d4225c9574d16096a"
  end

  resource "curl-cffi" do
    url "https://files.pythonhosted.org/packages/48/5b/89fcfebd3e5e85134147ac99e9f2b2271165fd4d71984fc65da5f17819b7/curl_cffi-0.15.0.tar.gz"
    sha256 "ea0c67652bf6893d34ee0f82c944f37e488f6147e9421bef1771cc6545b02ded"
  end

  resource "fastapi" do
    url "https://files.pythonhosted.org/packages/source/f/fastapi/fastapi-0.115.12.tar.gz"
    sha256 "1e2c2a2646905f9e83d32f04a3f86aff4a286669c6c950ca95b5fd68c2602681"
  end

  resource "h11" do
    url "https://files.pythonhosted.org/packages/source/h/h11/h11-0.14.0.tar.gz"
    sha256 "8f19fbbe99e72420ff35c00b27a34cb9937e902a8b810e2c88300c6f0a3b699d"
  end

  resource "httpcore" do
    url "https://files.pythonhosted.org/packages/source/h/httpcore/httpcore-1.0.8.tar.gz"
    sha256 "86e94505ed24ea06514883fd44d2bc02d90e77e7979c8eb71b90f41d364a1bad"
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
    sha256 "12f65c9b470abda6dc35cf8e63cc574b1c52b11df2c86030af0ac09b01b13ea9"
  end

  resource "jinja2" do
    url "https://files.pythonhosted.org/packages/source/J/Jinja2/jinja2-3.1.6.tar.gz"
    sha256 "0137fb05990d35f1275a587e9aee6d56da821fc83491a0fb838183be43f66d6d"
  end

  resource "markdown-it-py" do
    url "https://files.pythonhosted.org/packages/source/m/markdown-it-py/markdown_it_py-4.0.0.tar.gz"
    sha256 "cb0a2b4aa34f932c007117b194e945bd74e0ec24133ceb5bac59009cda1cb9f3"
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
    sha256 "7471657138c16adad9322fe3070c0116dd6c3ad8d649300e3cbdfe91f4db4ec3"
  end

  resource "pydantic-core" do
    url "https://files.pythonhosted.org/packages/source/p/pydantic_core/pydantic_core-2.33.1.tar.gz"
    sha256 "bcc9c6fdb0ced789245b02b7d6603e17d1563064ddcfc36f046b61c0c05dd9df"
  end

  resource "pygments" do
    url "https://files.pythonhosted.org/packages/source/P/Pygments/pygments-2.19.1.tar.gz"
    sha256 "61c16d2a8576dc0649d9f39e089b5f02bcd27fba10d8fb4dcc28173f7a45151f"
  end

  resource "pycparser" do
    url "https://files.pythonhosted.org/packages/1b/7d/92392ff7815c21062bea51aa7b87d45576f649f16458d78b7cf94b9ab2e6/pycparser-3.0.tar.gz"
    sha256 "600f49d217304a5902ac3c37e1281c9fe94e4d0489de643a9504c5cdfdfc6b29"
  end

  resource "python-dotenv" do
    url "https://files.pythonhosted.org/packages/source/p/python-dotenv/python_dotenv-1.1.0.tar.gz"
    sha256 "41f90bc6f5f177fb41f53e87666db362025010eb28f60a01c9143bfa33a2b2d5"
  end

  resource "python-multipart" do
    url "https://files.pythonhosted.org/packages/source/p/python-multipart/python_multipart-0.0.20.tar.gz"
    sha256 "8dd0cab45b8e23064ae09147625994d090fa46f5b0d1e13af944c331a7fa9d13"
  end

  resource "python-telegram-bot" do
    url "https://files.pythonhosted.org/packages/source/p/python-telegram-bot/python_telegram_bot-21.11.1.tar.gz"
    sha256 "2abda5202f27a838f35e8140e5292af0f4f8fad6c2e5123b2defadd5f4e8ca02"
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
    sha256 "f4324edc670a0f49750a81b895f35c3adb843cca46f0530f79fc1babb23789dc"
  end

  resource "starlette" do
    url "https://files.pythonhosted.org/packages/source/s/starlette/starlette-0.46.1.tar.gz"
    sha256 "3c88d58ee4bd1bb807c0d1acb381838afc7752f9ddaec81bbe4383611d833230"
  end

  resource "tzlocal" do
    url "https://files.pythonhosted.org/packages/source/t/tzlocal/tzlocal-5.3.1.tar.gz"
    sha256 "cceffc7edecefea1f595541dbd6e990cb1ea3d19bf01b2809f362a03dd7921fd"
  end

  resource "typing-inspection" do
    url "https://files.pythonhosted.org/packages/source/t/typing_inspection/typing_inspection-0.4.2.tar.gz"
    sha256 "ba561c48a67c5958007083d386c3295464928b01faa735ab8547c5692e87f464"
  end

  resource "typing-extensions" do
    url "https://files.pythonhosted.org/packages/source/t/typing_extensions/typing_extensions-4.13.2.tar.gz"
    sha256 "e6c81219bd689f51865d9e372991c540bda33a0379d5573cddb9a3a23f7caaef"
  end

  resource "uvicorn" do
    url "https://files.pythonhosted.org/packages/source/u/uvicorn/uvicorn-0.34.0.tar.gz"
    sha256 "404051050cd7e905de2c9a7e61790943440b3416f49cb409f965d9dcd0fa73e9"
  end

  resource "uvloop" do
    url "https://files.pythonhosted.org/packages/source/u/uvloop/uvloop-0.21.0.tar.gz"
    sha256 "3bf12b0fda68447806a7ad847bfa591613177275d35b6724b1ee573faa3704e3"
  end

  resource "watchfiles" do
    url "https://files.pythonhosted.org/packages/source/w/watchfiles/watchfiles-1.0.5.tar.gz"
    sha256 "b7529b5dcc114679d43827d8c35a07c493ad6f083633d573d81c660abc5979e9"
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
      CLAUDE_AGENT_AUTO_PROXY: "1",
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

      The Homebrew service auto-starts the bundled local proxy by default.

      Or run it manually in the foreground:

        claude-agent server --with-proxy

      Optional: inspect the proxy directly:

        claude-agent-proxy

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
