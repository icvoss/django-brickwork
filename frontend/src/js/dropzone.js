// bwDropzone: the file dropzone behaviour (BR-BW-INPUT-003, 0.13.0,
// brickwork#57).
//
// Public shape (semver-public, BR-BW-JS-004/005):
//   Alpine.data("bwDropzone", ...) with no config
//   state   isDragOver (boolean), fileNames (array of strings)
//   events  bw:dropzone:change (detail { files: [name, ...] }), a bubbling
//           CustomEvent dispatched from the component root (BR-BW-HTMX-004:
//           optional convention, never load-bearing).
//
// DOM contract this module enhances (_dropzone.html renders the floor;
// BR-BW-HTMX-006). The no-JS floor is a native <input type="file"> the
// wrapping <label> makes clickable; this module NEVER replaces or hides it
// from the accessibility tree (only CSS visually hides it, focusable and
// keyboard-activatable throughout):
//
//   <label class="bw-dropzone" x-data="bwDropzone()" data-bw-dropzone>
//     <input data-bw-dropzone-input type="file">   the real form control
//     <ul data-bw-dropzone-files>                  selected-file-name list
//
// Drag-over state ([data-bw-drag-over] on the root) is presentation only:
// dropping a file still requires the OS to hand it to the native input's own
// drop handling (a <label> wrapping a file input already forwards a drop
// onto it in every evergreen browser), so this module's dragover/drop
// handlers only toggle the visual state and never call preventDefault() in
// a way that would stop the native drop from reaching the input.
//
// Motion is CSS-owned: this module only toggles state and never sequences
// animation (BR-BW-TOK-009 lives entirely in the component CSS).

function dispatch(el, name, detail) {
  el.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

export default function dropzone() {
  return {
    isDragOver: false,
    fileNames: [],

    _root: null,
    _input: null,
    _files: null,

    init() {
      const root = this.$el;
      this._root = root;
      this._input = root.querySelector("[data-bw-dropzone-input]");
      this._files = root.querySelector("[data-bw-dropzone-files]");
      if (!this._input || !this._files) return; // floor markup absent: stay inert

      this._input.addEventListener("change", () => this._onChange());
      // preventDefault on dragover is required for the drop event to fire at
      // all (default browser behaviour otherwise opens the file); the native
      // input beneath still receives the OS drop independently.
      root.addEventListener("dragover", (event) => {
        event.preventDefault();
        this.isDragOver = true;
        root.setAttribute("data-bw-drag-over", "");
      });
      root.addEventListener("dragleave", () => this._clearDragOver());
      root.addEventListener("drop", () => this._clearDragOver());
    },

    _clearDragOver() {
      this.isDragOver = false;
      this._root.removeAttribute("data-bw-drag-over");
    },

    _onChange() {
      this.fileNames = Array.from(this._input.files || []).map((file) => file.name);
      this._renderFiles();
      dispatch(this._root, "bw:dropzone:change", { files: this.fileNames });
    },

    _renderFiles() {
      this._files.replaceChildren();
      for (const name of this.fileNames) {
        const item = document.createElement("li");
        item.className = "bw-dropzone__file";
        item.textContent = name;
        this._files.appendChild(item);
      }
    },
  };
}
