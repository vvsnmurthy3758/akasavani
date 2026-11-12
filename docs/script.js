// Interactive preview for the static GitHub Pages site.
// It plays pre-generated clips (0.7x, 1.0x, 1.5x) that match the closest
// settings, so visitors can feel the UI without a running server.

(function () {
  var text = document.getElementById("mock-text");
  var speaker = document.getElementById("mock-speaker");
  var speed = document.getElementById("mock-speed");
  var speedValue = document.getElementById("mock-speed-value");
  var speakBtn = document.getElementById("mock-speak");
  var status = document.getElementById("mock-status");
  var audio = document.getElementById("mock-audio");

  function clipFor(spk, value) {
    if (spk === "p376") return "assets/sample-voice2.mp3";
    if (value < 0.85) return "assets/sample-slow.mp3";
    if (value > 1.25) return "assets/sample-fast.mp3";
    return "assets/sample-normal.mp3";
  }

  speed.addEventListener("input", function () {
    speedValue.textContent = Number(speed.value).toFixed(2) + "\u00D7";
  });

  speakBtn.addEventListener("click", function () {
    if (!text.value.trim()) {
      status.textContent = "Type some text first.";
      return;
    }
    status.textContent = "Synthesizing\u2026";
    speakBtn.disabled = true;
    var value = Number(speed.value);
    var src = clipFor(speaker.value, value);

    setTimeout(function () {
      audio.src = src;
      audio.hidden = false;
      var played = audio.play();
      if (played && played.catch) {
        played.catch(function () { /* autoplay may be blocked; controls are shown */ });
      }
      status.textContent = "Preview \u2014 pre-generated clip.";
      speakBtn.disabled = false;
    }, 700);
  });
})();
