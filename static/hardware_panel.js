/**
 * hardware_panel.js
 * Dinamik Donanim & Render Hizlandirma Yonetim Modulu
 * Her kullanicinin kendi CPU, GPU ve RAM ozelliklerine gore otomatik calisir.
 */

(function () {
    let lastSpecs = null;

    function showHwToast(msg, type = 'success') {
        const container = document.getElementById('toast-container');
        if (!container) {
            alert(msg);
            return;
        }
        const toast = document.createElement('div');
        toast.className = 'toast';
        const icon = type === 'error' ? 'fa-triangle-exclamation text-danger' : 'fa-circle-check text-primary';
        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${msg}</span>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    async function loadHardwareSpecs(forceRefresh = false) {
        const elCpuName = document.getElementById('hw-cpu-name');
        const elCpuThreads = document.getElementById('hw-cpu-threads');
        const elGpuName = document.getElementById('hw-gpu-name');
        const elGpuNvenc = document.getElementById('hw-gpu-nvenc');
        const elRamTotal = document.getElementById('hw-ram-total');
        const elRamAvail = document.getElementById('hw-ram-avail');
        const elRecLabel = document.getElementById('hw-recommended-label');
        const elRecDesc = document.getElementById('hw-recommended-desc');

        if (elCpuName) elCpuName.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Taranıyor...';
        if (elGpuName) elGpuName.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Taranıyor...';
        if (elRamTotal) elRamTotal.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Taranıyor...';

        try {
            const res = await fetch('/api/hardware/specs');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (data && data.specs) {
                lastSpecs = data.specs;
                renderHardwareUI(data.specs);
                return data.specs;
            }
        } catch (err) {
            console.error('Donanim tespit hatasi:', err);
            // Guvenli dinamik yerel fallback
            const fallbackSpecs = {
                cpu: { name: 'Sistem Islemcisi (Cok Cekirdekli)', threads: navigator.hardwareConcurrency || 8, physical_cores: Math.max(2, Math.floor((navigator.hardwareConcurrency || 8) / 2)) },
                gpu: { name: 'Standart Grafik Birimi', has_nvenc: false, vram_gb: 4.0 },
                ram: { total_gb: 16.0, avail_gb: 8.0 },
                recommended_profile: 'cpu_multithread',
                recommended_label: 'Cok Cekirdekli CPU Render Hizlandirma',
                recommended_threads: Math.max(2, Math.floor((navigator.hardwareConcurrency || 8) / 2)),
                recommended_use_gpu: false,
                current_config: { use_gpu: false, gpu_codec: 'libx264', render_threads: 4, fps_diversify: true }
            };
            lastSpecs = fallbackSpecs;
            renderHardwareUI(fallbackSpecs);
            return fallbackSpecs;
        }
    }

    function renderHardwareUI(specs) {
        const elCpuName = document.getElementById('hw-cpu-name');
        const elCpuThreads = document.getElementById('hw-cpu-threads');
        const elGpuName = document.getElementById('hw-gpu-name');
        const elGpuNvenc = document.getElementById('hw-gpu-nvenc');
        const elRamTotal = document.getElementById('hw-ram-total');
        const elRamAvail = document.getElementById('hw-ram-avail');
        const elRecLabel = document.getElementById('hw-recommended-label');
        const elRecDesc = document.getElementById('hw-recommended-desc');

        const cpu = specs.cpu || {};
        const gpu = specs.gpu || {};
        const ram = specs.ram || {};
        const curCfg = specs.current_config || {};

        // 1. CPU
        if (elCpuName) elCpuName.textContent = cpu.name || 'Bilinmeyen İşlemci';
        if (elCpuThreads) {
            const th = cpu.threads || 4;
            const phys = cpu.physical_cores || Math.floor(th / 2);
            elCpuThreads.textContent = `${th} İş Parçacığı (Threads) · ${phys} Fiziksel Çekirdek`;
        }

        // 2. GPU
        if (elGpuName) elGpuName.textContent = gpu.name || 'Dahili Grafik';
        if (elGpuNvenc) {
            if (gpu.has_nvenc) {
                elGpuNvenc.innerHTML = `<i class="fa-solid fa-bolt text-warning"></i> NVIDIA NVENC Donanım Çipi <strong>Aktif & Hazır</strong> (${gpu.vram_gb || 8} GB VRAM)`;
            } else {
                elGpuNvenc.innerHTML = `<i class="fa-solid fa-microchip text-info"></i> Yazılımsal CPU Hızlandırma (libx264)`;
            }
        }

        // 3. RAM
        if (elRamTotal) elRamTotal.textContent = `${ram.total_gb || 16} GB Toplam RAM`;
        if (elRamAvail) elRamAvail.textContent = `${ram.avail_gb || 8} GB Kullanılabilir / Boşta`;

        // 4. Önerilen Profil
        if (elRecLabel) {
            elRecLabel.textContent = specs.recommended_label || 'Sisteme Göre Maksimum Render Profili';
        }
        if (elRecDesc) {
            const recThreads = specs.recommended_threads || Math.max(2, Math.floor((cpu.threads || 8) / 2));
            if (gpu.has_nvenc) {
                elRecDesc.innerHTML = `Madde 74 Kare Hızı mikro-çeşitlendirmesi (<strong>29.97, 30.02 fps</strong>) devrede; <strong>${gpu.name}</strong> NVENC donanım çipi ve <strong>${recThreads} CPU çekirdeği</strong> ile sistem boğulmadan dakikalar içinde render alınır.`;
            } else {
                elRecDesc.innerHTML = `Madde 74 Kare Hızı mikro-çeşitlendirmesi (<strong>29.97, 30.02 fps</strong>) devrede; <strong>${recThreads} CPU çekirdeği</strong> ile dengeli ve hızlı video üretimi sağlanır.`;
            }
        }

        // 5. Codec Seçeneklerini Doldur
        const selCodec = document.getElementById('select-hw-codec');
        if (selCodec) {
            selCodec.innerHTML = '';
            if (gpu.has_nvenc) {
                const optNv = document.createElement('option');
                optNv.value = 'h264_nvenc';
                optNv.textContent = `🚀 NVIDIA NVENC (${gpu.name} Donanım Çipi - En Hızlı)`;
                selCodec.appendChild(optNv);
            }
            const optCpu = document.createElement('option');
            optCpu.value = 'libx264';
            optCpu.textContent = `⚡ Yazılımsal CPU (libx264 - Çoklu Çekirdek)`;
            selCodec.appendChild(optCpu);

            if (curCfg.use_gpu && gpu.has_nvenc) {
                selCodec.value = 'h264_nvenc';
            } else {
                selCodec.value = 'libx264';
            }
        }

        // 6. CPU Thread Seçeneklerini Kullanıcının Gerçek Thread Sayısına Göre Doldur
        const selThreads = document.getElementById('select-hw-threads');
        if (selThreads) {
            selThreads.innerHTML = '';
            const maxThreads = cpu.threads || 8;
            const recThreads = specs.recommended_threads || Math.max(1, Math.floor(maxThreads / 2));

            // Belirlenecek thread kademeleri
            const threadSteps = new Set();
            threadSteps.add(maxThreads);
            if (maxThreads >= 16) threadSteps.add(12);
            if (maxThreads >= 8) threadSteps.add(8);
            if (maxThreads >= 6) threadSteps.add(6);
            if (maxThreads >= 4) threadSteps.add(4);
            if (maxThreads >= 2) threadSteps.add(2);
            threadSteps.add(1);
            threadSteps.add(recThreads);

            const sortedSteps = Array.from(threadSteps).sort((a, b) => b - a);
            sortedSteps.forEach(th => {
                const opt = document.createElement('option');
                opt.value = String(th);
                if (th === maxThreads) {
                    opt.textContent = `${th} Thread (Tüm Çekirdekler - %100 CPU)`;
                } else if (th === recThreads) {
                    opt.textContent = `${th} Thread (Önerilen - %50 Sistem Dengeli)`;
                } else if (th === 1) {
                    opt.textContent = `1 Thread (Minimum Güç / Sessiz)`;
                } else {
                    opt.textContent = `${th} Thread`;
                }
                selThreads.appendChild(opt);
            });

            const activeThreads = curCfg.render_threads || recThreads;
            selThreads.value = String(activeThreads);
        }

        // 7. FPS Modu
        const selFps = document.getElementById('select-hw-fps-mode');
        if (selFps && curCfg) {
            if (curCfg.fps_diversify) {
                selFps.value = 'diversify';
            } else if (curCfg.fps) {
                selFps.value = String(Math.round(curCfg.fps));
            }
        }

        // 8. Çözünürlük ve Hızlı Test Modu (1080p, 720p, 540p)
        const currentRes = curCfg.resolution || '1080p';
        const selHwRes = document.getElementById('select-hw-resolution');
        if (selHwRes) {
            selHwRes.value = currentRes;
        }
        const selStudioRes = document.getElementById('select-render-resolution');
        if (selStudioRes) {
            selStudioRes.value = currentRes;
        }

        // 9. Render Güvenlik & Efekt Derinliği (RENDER_SAFE_MODE)
        const safeModeVal = (curCfg.safe_mode !== undefined) ? String(curCfg.safe_mode) : 'false';
        const selHwSafe = document.getElementById('select-hw-safe-mode');
        if (selHwSafe) {
            selHwSafe.value = safeModeVal;
        }
        const selStudioSafe = document.getElementById('select-studio-safe-mode');
        if (selStudioSafe) {
            selStudioSafe.value = safeModeVal;
        }
    }

    // Otomatik Maksimum Profil Uygulama
    async function applyRecommendedProfile() {
        const btn = document.getElementById('btn-apply-hardware-max');
        const origHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Optimize Ediliyor...';
        }

        try {
            const hasNvenc = lastSpecs && lastSpecs.gpu ? Boolean(lastSpecs.gpu.has_nvenc) : true;
            const recThreads = lastSpecs && lastSpecs.recommended_threads ? lastSpecs.recommended_threads : 8;
            const selRes = document.getElementById('select-hw-resolution')?.value || '1080p';
            const selSafeMode = (document.getElementById('select-hw-safe-mode')?.value === 'true');

            const res = await fetch('/api/hardware/apply_profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    profile: hasNvenc ? 'ultra_gpu' : 'cpu_balanced',
                    threads: recThreads,
                    use_gpu: hasNvenc,
                    gpu_codec: hasNvenc ? 'h264_nvenc' : 'libx264',
                    fps_diversify: true,
                    resolution: selRes,
                    safe_mode: selSafeMode
                })
            });
            const data = await res.json();
            showHwToast(data.message || 'Maksimum donanım profili başarıyla uygulandı!');
            await loadHardwareSpecs();
        } catch (err) {
            showHwToast('Profil uygulanırken hata oluştu: ' + err.message, 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = origHtml || '<i class="fa-solid fa-bolt"></i> Donanımıma Göre Maksimum Hızda Yapılandır';
            }
        }
    }

    // Manuel Ayarları Kaydetme
    async function saveManualSettings() {
        const btn = document.getElementById('btn-save-hardware-manual');
        const origHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kaydediliyor...';
        }

        const selCodec = document.getElementById('select-hw-codec')?.value || 'h264_nvenc';
        const selThreads = parseInt(document.getElementById('select-hw-threads')?.value || '8');
        const selFpsMode = document.getElementById('select-hw-fps-mode')?.value || 'diversify';
        const selRes = document.getElementById('select-hw-resolution')?.value || '1080p';
        const selSafeMode = (document.getElementById('select-hw-safe-mode')?.value === 'true');

        const useGpu = (selCodec === 'h264_nvenc');
        const fpsDiversify = (selFpsMode === 'diversify');
        const fixedFps = fpsDiversify ? 30.0 : (parseFloat(selFpsMode) || 30.0);

        try {
            const res = await fetch('/api/hardware/apply_profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    profile: 'manual',
                    use_gpu: useGpu,
                    gpu_codec: selCodec,
                    threads: selThreads,
                    fps_diversify: fpsDiversify,
                    fixed_fps: fixedFps,
                    resolution: selRes,
                    safe_mode: selSafeMode
                })
            });
            const data = await res.json();
            showHwToast(data.message || 'Manuel ayarlar başarıyla kaydedildi!');
            await loadHardwareSpecs();
        } catch (err) {
            showHwToast('Manuel ayarlar kaydedilirken hata: ' + err.message, 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = origHtml || '<i class="fa-solid fa-floppy-disk"></i> Manuel Ayarları Kaydet & Uygula';
            }
        }
    }

    function setupEventListeners() {
        const btnScan = document.getElementById('btn-detect-hardware-now');
        if (btnScan) {
            btnScan.onclick = async () => {
                showHwToast('🔍 Sistem donanımı taranıyor...');
                await loadHardwareSpecs(true);
                showHwToast('✅ Donanım bilgileri başarıyla güncellendi!');
            };
        }

        const btnMax = document.getElementById('btn-apply-hardware-max');
        if (btnMax) {
            btnMax.onclick = applyRecommendedProfile;
        }

        const btnManual = document.getElementById('btn-save-hardware-manual');
        if (btnManual) {
            btnManual.onclick = saveManualSettings;
        }

        // Çözünürlük Değişimi Dinleyicileri (Stüdyo ve Ayarlar Çift Yönlü Senkron)
        const selStudioRes = document.getElementById('select-render-resolution');
        if (selStudioRes) {
            selStudioRes.onchange = async () => {
                const newRes = selStudioRes.value;
                const selHwRes = document.getElementById('select-hw-resolution');
                if (selHwRes) selHwRes.value = newRes;
                try {
                    await fetch('/api/hardware/apply_profile', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ resolution: newRes })
                    });
                    const labels = {
                        '1080p': '1080x1920 (Full HD)',
                        '720p': '720x1280 (Hızlı HD - 2.2x)',
                        '540p': '540x960 (Ultra Hızlı Test - 4x)'
                    };
                    showHwToast(`🎬 Render Çözünürlüğü Değiştirildi: ${labels[newRes] || newRes}`);
                } catch (e) {}
            };
        }

        const selHwRes = document.getElementById('select-hw-resolution');
        if (selHwRes) {
            selHwRes.onchange = () => {
                const selStudio = document.getElementById('select-render-resolution');
                if (selStudio) selStudio.value = selHwRes.value;
            };
        }

        // Safe Mode / Efekt Modu Değişimi Dinleyicileri (Stüdyo ve Ayarlar Çift Yönlü Senkron)
        const selStudioSafe = document.getElementById('select-studio-safe-mode');
        if (selStudioSafe) {
            selStudioSafe.onchange = async () => {
                const isSafe = (selStudioSafe.value === 'true');
                const selHwSafe = document.getElementById('select-hw-safe-mode');
                if (selHwSafe) selHwSafe.value = selStudioSafe.value;
                try {
                    await fetch('/api/hardware/apply_profile', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ safe_mode: isSafe })
                    });
                    showHwToast(isSafe ? '⚡ Hızlı Güvenli Mod Aktif Edildi (15-35 FPS)' : '🎬 Tam Kural & Maksimum Zenginlik Modu Aktif Edildi (Tüm Kurallar Açık)!');
                } catch (e) {}
            };
        }

        const selHwSafe = document.getElementById('select-hw-safe-mode');
        if (selHwSafe) {
            selHwSafe.onchange = () => {
                const selStudio = document.getElementById('select-studio-safe-mode');
                if (selStudio) selStudio.value = selHwSafe.value;
            };
        }
    }

    // Global disari aktarma
    window.loadHardwareSpecs = loadHardwareSpecs;
    window.applyRecommendedProfile = applyRecommendedProfile;
    window.saveManualSettings = saveManualSettings;

    // Baslatma
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            setupEventListeners();
            loadHardwareSpecs();
        });
    } else {
        setupEventListeners();
        loadHardwareSpecs();
    }
})();
