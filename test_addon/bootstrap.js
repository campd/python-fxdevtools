function install(data) {
}

function startup(data, reason) {
  dump("Importing\n");
  try {
    let {DebuggerServer} = Components.utils.import("resource://gre/modules/devtools/dbg-server.jsm", {});
    dump("Done importing");
    DebuggerServer.init(false);
    DebuggerServer.addBrowserActors();
    DebuggerServer.openListener(6789);

    dump("ADDON SUCCESSFULLY INSTALLED")
  } catch(ex) {
    dump(ex + "\n");
  }
}
