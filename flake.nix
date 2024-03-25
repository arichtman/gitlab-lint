{
  description = "GitLab-Lint";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/release-23.11";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix.url = "github:nix-community/poetry2nix";
    poetry2nix.inputs.nixpkgs.follows = "nixpkgs";
  };
  outputs = {
    self,
    nixpkgs,
    poetry2nix,
    flake-utils,
    ...
  } @ inputs:
    flake-utils.lib.eachSystem [ "x86_64-linux" "x86_64-darwin" "aarch64-darwin" ]
    (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [poetry2nix.overlays.default];
        };
        poetryEnv = pkgs.poetry2nix.mkPoetryEnv {
          projectDir = ./.;
          editablePackageSources = {
            gitlab-lint = ./src;
            preferWheels = true;
          };
        };
      in {
        devShells.default = with pkgs;
          mkShell {
            nativeBuildInputs = [
              poetryEnv
            ];
            shellHook = ''
              pre-commit install --install-hooks
            '';
          };
      }
    );
}
