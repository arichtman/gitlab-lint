{
  description = "GitLab-Lint";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    poetry2nix.url = "github:nix-community/poetry2nix";
  };
  outputs = {
    self,
    nixpkgs,
    poetry2nix,
    flake-utils,
    ...
  } @ inputs:
    flake-utils.lib.eachSystem [ "x86_64-linux" "x86_64-darwin" ]
    (system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
        inherit (poetry2nix.legacyPackages.${system}) mkPoetryEnv mkPoetryApplication mkPoetryEditablePackage;
        poetryEnv = mkPoetryEnv {
          projectDir = ./.;
          editablePackageSources = {
            gitlab-lint = ./src;
          };
        };
      in {
        devShells.default = with pkgs;
          mkShell {
            nativeBuildInputs = [
              poetryEnv
              poetry
            ];
            shellHook = ''
              pre-commit install --install-hooks
            '';
          };
      }
    );
}
