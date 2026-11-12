// Interactive preview for the static GitHub Pages site.
// It plays pre-generated clips that match the closest settings, so visitors
// can feel the UI without a running server.

(function () {
  var lang = document.getElementById("mock-lang");
  var text = document.getElementById("mock-text");
  var speaker = document.getElementById("mock-speaker");
  var enVoice = document.getElementById("mock-en-voice");
  var teVoice = document.getElementById("mock-telugu-voice");
  var teVoiceRow = document.getElementById("mock-te-voice");
  var speed = document.getElementById("mock-speed");
  var speedValue = document.getElementById("mock-speed-value");
  var speakBtn = document.getElementById("mock-speak");
  var status = document.getElementById("mock-status");
  var audio = document.getElementById("mock-audio");

  var SAMPLES = {
    en: "Hi there. I am a local text to speech assistant.",
    te: "\u0C28\u0C2E\u0C38\u0C4D\u0C15\u0C3E\u0C30\u0C02! \u0C07\u0C26\u0C3F \u0C06\u0C15\u0C3E\u0C36\u0C35\u0C3E\u0C23\u0C3F."
  };

  var TELUGU_CLIPS = {
    padmavathi: "assets/sample-telugu.mp3",
    venkatesh: "assets/sample-telugu-venkatesh.mp3",
    maya: "assets/sample-telugu-maya.mp3"
  };

  function clipFor(langCode, spk, value) {
    if (langCode === "te") {
      if (value < 0.85 && teVoice.value === "padmavathi") {
        return "assets/sample-telugu-slow.mp3";
      }
      return TELUGU_CLIPS[teVoice.value] || TELUGU_CLIPS.padmavathi;
    }
    if (spk === "b") return "assets/sample-voice2.mp3";
    if (value < 0.85) return "assets/sample-slow.mp3";
    if (value > 1.25) return "assets/sample-fast.mp3";
    return "assets/sample-normal.mp3";
  }

  lang.addEventListener("change", function () {
    var isTe = lang.value === "te";
    enVoice.style.display = isTe ? "none" : "";
    teVoiceRow.style.display = isTe ? "" : "none";
    text.value = SAMPLES[isTe ? "te" : "en"];
  });

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
    var src = clipFor(lang.value, speaker.value, value);

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
