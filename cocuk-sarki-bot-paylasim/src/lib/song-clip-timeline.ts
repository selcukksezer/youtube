/**
 * Master parca zaman cizelgesi: klipler sarkiyi BOSLUKSUZ ve TASMASIZ boler.
 *
 * Eski davranis: her klip tam `clipSeconds` uzunlugundaydi ve artan sure son
 * klibe ekleniyordu. 161.7 sn / 8 sn'de son klip 9.7 sn oluyordu — Flow 8 sn
 * video urettigi icin sarkinin sonundan ~1.7 sn goruntusuz kaliyor ve panel
 * "tahmini konusma suresi klip suresini asiyor" uyarisi veriyordu.
 *
 * Yeni davranis: klip sayisi yukari yuvarlanir (bir klip daha) ve sure TUM
 * kliplere esit dagitilir. Boylece hicbir klip `clipSeconds`i asmaz, arada
 * bosluk kalmaz ve son klip de dolu olur.
 *
 * Matematik guvencesi: n = ceil(D/L) icin D > (n-1)*L oldugundan pencere
 * D/n > L/2 olur — yani 8 sn'lik ayarda hicbir klip 4 sn'nin altina dusmez.
 */

export function songClipCount(audioDurationSeconds: number, clipSeconds: number): number {
  const sec = Math.max(2, clipSeconds || 8);
  const dur = Math.max(0.5, audioDurationSeconds);
  return Math.max(1, Math.ceil(dur / sec));
}

export function songClipAudioWindow(opts: {
  index: number;
  clipCount: number;
  clipSeconds: number;
  audioDurationSeconds: number;
}): { startSeconds: number; endSeconds: number; durationSeconds: number } {
  const index = Math.max(1, Math.round(opts.index));
  const clipCount = Math.max(1, Math.round(opts.clipCount));
  const clipSeconds = Math.max(2, opts.clipSeconds || 8);
  const audioDurationSeconds = Math.max(0.5, opts.audioDurationSeconds);

  // Esit pencere: sarki tam olarak klip sayisina bolunur.
  const perClip = audioDurationSeconds / clipCount;

  // Guvenlik: klip sayisi yetersiz verildiyse (ör. eski kayitli plan) pencere
  // clipSeconds'i asmasin — bu durumda sabit dilim + son klipte kalan kullanilir.
  if (perClip > clipSeconds) {
    const startSeconds = (index - 1) * clipSeconds;
    const isLast = index >= clipCount;
    const endSeconds = Math.min(audioDurationSeconds, isLast ? audioDurationSeconds : startSeconds + clipSeconds);
    return { startSeconds, endSeconds, durationSeconds: Math.max(0.2, endSeconds - startSeconds) };
  }

  const startSeconds = (index - 1) * perClip;
  // Son klipte kayan nokta artigini kapat: bitis tam olarak parca sonu.
  const endSeconds = index >= clipCount ? audioDurationSeconds : startSeconds + perClip;
  return { startSeconds, endSeconds, durationSeconds: Math.max(0.2, endSeconds - startSeconds) };
}
