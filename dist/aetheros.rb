class Aetheros < Formula
  desc "AetherOS - AI Operating System"
  homepage "https://aetheros.dev"
  url "https://github.com/aetheros/aetheros/releases/download/v0.16.0/aetheros-0.16.0.tar.gz"
  sha256 "COMPUTE_AFTER_RELEASE"
  license "MIT"

  def install
    bin.install "aetheros"
  end

  test do
    system "#{bin}/aetheros", "--version"
  end
end
