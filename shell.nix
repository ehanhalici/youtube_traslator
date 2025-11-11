{ pkgs ? import <nixpkgs> {} }:

let
  libs = [
    pkgs.gcc.cc.lib
    pkgs.zlib.out
  ];
in
pkgs.mkShell {
  buildInputs = [
    pkgs.uv
    pkgs.python312
  ] ++ libs;

  shellHook = ''
    for lib in ${pkgs.lib.concatStringsSep " " (map (p: "${p}/lib") libs)};
    do
      export LD_LIBRARY_PATH="$lib:$LD_LIBRARY_PATH"
    done

    echo "export LD_LIBRARY_PATH=$LD_LIBRARY_PATH" >> .venv/bin/activate
   '';
}
