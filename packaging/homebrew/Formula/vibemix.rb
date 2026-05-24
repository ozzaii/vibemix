# SPDX-License-Identifier: Apache-2.0
#
# Homebrew Formula scaffold for vibemix — open-source AI DJ co-host.
# Phase 69 Plan 69-04 (OSS-05): the URL and SHA256 are deterministic
# placeholders today; scripts/launch/sync_packaging.sh replaces them at
# real-cut time with the actual v0.1.0-rc1 release artifact + SHA.
#
# Verified by `brew audit --new packaging/homebrew/Formula/vibemix.rb`
# in .github/workflows/packaging-audit.yml. The actual tap publish to
# `bravoh-ai/homebrew-tap` is deferred to a future milestone — see
# docs/release-process.md "Homebrew + Scoop publish — split rationale".
class Vibemix < Formula
  desc "Free, open-source AI DJ co-host — listens, watches, and reacts"
  homepage "https://github.com/bravoh-ai/vibemix"
  url "https://github.com/bravoh-ai/vibemix/releases/download/v0.1.0-rc1/vibemix-v0.1.0-rc1-macos.dmg"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  version "0.1.0-rc1"
  license "Apache-2.0"

  depends_on :macos => :ventura

  def install
    # Real install logic lands when OSS-04 fires + sync_packaging.sh
    # replaces the placeholder SHA with the actual signed-DMG SHA-256.
    # The .dmg layout is the existing v4.0 cut: app bundle under /Applications.
    prefix.install Dir["*"]
  end

  test do
    # Smoke test runs at `brew test vibemix` install-time.
    # Confirms the binary launched via the .dmg responds to --version.
    assert_match "vibemix", shell_output("#{bin}/vibemix --version 2>&1", 1)
  end
end
