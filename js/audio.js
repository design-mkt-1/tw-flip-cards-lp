/* Top Win — the sound pool.

   Small, guarded, and silent until the visitor has touched the page. It exists
   here rather than in a campaign because js/shell.js already renders the mute
   button from `header.mute` and used to wire nothing to it: every campaign
   with audio wrote this file again, and the one that forgot shipped a speaker
   that did nothing.

   What a campaign declares, in campaign.js:

     sounds: {
       kick: 'campaign/assets/audio/kick.mp3',
       net:  'campaign/assets/audio/net.mp3'
     }

   and then plays through the shell:

     TW.sound('kick', 0.9)     name from that map, volume 0..1
     TW.muted()                true if the visitor has muted the page

   An empty map is the default and costs nothing: no Audio element is made, and
   js/shell.js renders no speaker unless `header.mute` is true as well.

   THE THREE THINGS THAT ARE NOT OBVIOUS

   1. `preload: 'none'` until the first gesture. Seven clips are ~160 kB that
      cannot make a sound before someone taps, so none of it belongs in the
      page load. unlock() raises it to 'auto' and primes each element inside
      the gesture, which is what buys playback later.
   2. The mute state is read and written inside try/catch. A storage that
      throws -- private mode, or an iframe with third-party storage blocked,
      and this is a landing page -- would otherwise kill this file at parse
      time, and with it every script after it in index.html.
   3. A clip that fails to load is set to null and simply never plays. A
      missing sound is not a reason for a landing page to stop working. */

(function () {
  'use strict';

  var KEY = 'tw-muted';
  var C = window.TW_CAMPAIGN || {};
  var FILES = C.sounds || {};

  var pool = {};
  var unlocked = false;
  var muted = false;

  try { muted = localStorage.getItem(KEY) === '1'; } catch (e) { /* private mode */ }

  function load() {
    Object.keys(FILES).forEach(function (name) {
      if (!FILES[name]) return;
      var a = new Audio();
      a.preload = 'none';
      a.src = FILES[name];
      a.addEventListener('error', function () { pool[name] = null; });
      pool[name] = a;
    });
  }

  /* Audio can only start inside a user gesture, so the first pointer or key
     event on the page is what primes the pool. Registered here rather than in
     a campaign: every campaign with sound needs it and none of them should be
     the one to remember. */
  function unlock() {
    if (unlocked) return;
    unlocked = true;
    Object.keys(pool).forEach(function (name) {
      var a = pool[name];
      if (!a) return;
      a.preload = 'auto';
      a.muted = true;
      var p = a.play();
      if (p && p.catch) p.catch(function () {});
      a.pause();
      a.currentTime = 0;
      a.muted = false;
    });
  }

  /* cloneNode, so the same clip can overlap itself -- two cards turned inside
     one another's tail, a whistle under a cheer. */
  function play(name, volume) {
    if (muted || !unlocked) return;
    var src = pool[name];
    if (!src) return;
    var node = src.cloneNode();
    node.volume = typeof volume === 'number' ? volume : 1;
    var p = node.play();
    if (p && p.catch) p.catch(function () {});
  }

  function setMuted(next) {
    muted = !!next;
    try { localStorage.setItem(KEY, muted ? '1' : '0'); } catch (e) { /* private mode */ }
    /* Every speaker on the page, because the shell renders one and a campaign
       is free to draw its own beside the mechanic. */
    Array.prototype.forEach.call(document.querySelectorAll('.tw-mute'), function (btn) {
      btn.setAttribute('aria-pressed', String(muted));
    });
  }

  if (Object.keys(FILES).length) {
    load();
    window.addEventListener('pointerdown', unlock);
    window.addEventListener('keydown', unlock);
  }

  window.TWAudio = {
    unlock:   unlock,
    play:     play,
    setMuted: setMuted,
    isMuted:  function () { return muted; },
    toggle:   function () { setMuted(!muted); },
    /* js/shell.js asks this before wiring the button: a campaign that declared
       header.mute but no clips gets no speaker rather than a dead one. */
    has:      function () { return Object.keys(pool).length > 0; }
  };
}());
