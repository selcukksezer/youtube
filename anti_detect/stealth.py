"""
Stealth JavaScript Injection & Chromium Launch Arguments
Covers items: 3, 4, 5, 6, 9, 10, 13, 19, 20, 21, 23, 27
"""
from typing import List, Optional
from .profile import BrowserProfile, STANDARD_MACOS_FONTS

def generate_stealth_js(profile: BrowserProfile) -> str:
    """
    Generates comprehensive JavaScript injection payload to execute before page scripts.
    Fulfills Rules 3, 4, 5, 6, 13, 19, 20, 21, 27.
    """
    noise = profile.canvas_noise_seed
    vendor = profile.webgl_vendor
    renderer = profile.webgl_renderer
    concurrency = profile.hardware_concurrency
    memory = profile.device_memory
    vw = profile.viewport_width
    vh = profile.viewport_height
    font_whitelist_js = ", ".join([f"'{f.lower()}'" for f in STANDARD_MACOS_FONTS])

    return f"""
    // ─── [RULE 19] HEADLESS & AUTOMATION CLOAKING ────────────────
    Object.defineProperty(navigator, 'webdriver', {{
        get: () => undefined,
        configurable: true
    }});

    // ─── [RULE 27] CLIENT HINTS (sec-ch-ua & navigator.userAgentData) ───
    (() => {{
        const brands = [
            {{ brand: 'Chromium', version: '128' }},
            {{ brand: 'Not;A=Brand', version: '24' }},
            {{ brand: 'Google Chrome', version: '128' }}
        ];
        const highEntropyValues = {{
            architecture: 'arm',
            bitness: '64',
            brands: brands,
            mobile: false,
            model: '',
            platform: 'macOS',
            platformVersion: '14.5.0',
            uaFullVersion: '128.0.6613.119',
            fullVersionList: brands
        }};
        Object.defineProperty(navigator, 'userAgentData', {{
            get: () => ({{
                brands: brands,
                mobile: false,
                platform: 'macOS',
                getHighEntropyValues: (hints) => Promise.resolve(highEntropyValues),
                toJSON: () => ({{ brands, mobile: false, platform: 'macOS' }})
            }}),
            configurable: true
        }});
    }})();

    // Deep window.chrome mock (Rule 19)
    window.chrome = {{
        app: {{
            isInstalled: false,
            InstallState: {{ DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }},
            RunningState: {{ CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }}
        }},
        runtime: {{
            OnInstalledReason: {{}},
            OnRestartRequiredReason: {{}},
            PlatformArch: {{ ARM64: 'arm64', X86_64: 'x86-64' }},
            PlatformNaclArch: {{ ARM: 'arm', X86_64: 'x86-64' }},
            PlatformOs: {{ MAC: 'mac' }},
            RequestUpdateCheckStatus: {{ NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' }}
        }},
        loadTimes: function() {{
            return {{
                requestTime: performance.timeOrigin / 1000,
                startLoadTime: performance.timeOrigin / 1000,
                commitLoadTime: performance.timeOrigin / 1000 + 0.12,
                finishDocumentLoadTime: performance.timeOrigin / 1000 + 0.35,
                firstPaintTime: performance.timeOrigin / 1000 + 0.28,
                firstPaintAfterLoadTime: 0,
                navigationType: 'Other',
                wasFetchedViaSpdy: true,
                wasNpnNegotiated: true,
                npnNegotiatedProtocol: 'h2',
                wasAlternateProtocolAvailable: false,
                connectionInfo: 'h2'
            }};
        }},
        csi: function() {{
            return {{
                startE: performance.timeOrigin,
                onloadT: performance.timeOrigin + 350,
                pageT: 420.5,
                tran: 15
            }};
        }}
    }};

    // Notification.permission mock (Rule 19)
    if (typeof window.Notification === 'undefined') {{
        window.Notification = {{
            permission: 'default',
            requestPermission: () => Promise.resolve('default')
        }};
    }} else {{
        try {{
            Object.defineProperty(Notification, 'permission', {{ get: () => 'default' }});
        }} catch(e) {{}}
    }}

    // navigator.permissions.query mock for notifications (Rule 19)
    if (navigator.permissions && navigator.permissions.query) {{
        const origPermQuery = navigator.permissions.query;
        navigator.permissions.query = function(param) {{
            if (param && param.name === 'notifications') {{
                return Promise.resolve({{ state: 'default', onchange: null }});
            }}
            return origPermQuery.call(this, param);
        }};
    }}

    // Plugins & MimeTypes Array Cloaking (Rule 19 - never empty)
    Object.defineProperty(navigator, 'plugins', {{
        get: () => [
            {{ name: "PDF Viewer", filename: "internal-pdf-viewer", description: "Portable Document Format" }},
            {{ name: "Chrome PDF Viewer", filename: "internal-pdf-viewer", description: "Portable Document Format" }},
            {{ name: "Chromium PDF Viewer", filename: "internal-pdf-viewer", description: "Portable Document Format" }},
            {{ name: "Microsoft Edge PDF Viewer", filename: "internal-pdf-viewer", description: "Portable Document Format" }},
            {{ name: "WebKit built-in PDF", filename: "internal-pdf-viewer", description: "Portable Document Format" }}
        ]
    }});

    Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {concurrency} }});
    Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {memory} }});

    // ─── [RULE 21] SCREEN RESOLUTION & VIEWPORT BOUNDS LOCK ───────
    (() => {{
        const sw = {vw};
        const sh = {vh};
        Object.defineProperty(screen, 'width', {{ get: () => sw }});
        Object.defineProperty(screen, 'height', {{ get: () => sh }});
        Object.defineProperty(screen, 'availWidth', {{ get: () => sw }});
        Object.defineProperty(screen, 'availHeight', {{ get: () => sh - 38 }}); // macOS top menu bar
        Object.defineProperty(window, 'innerWidth', {{ get: () => sw }});
        Object.defineProperty(window, 'innerHeight', {{ get: () => sh - 85 }}); // Chrome toolbar
        Object.defineProperty(window, 'outerWidth', {{ get: () => sw }});
        Object.defineProperty(window, 'outerHeight', {{ get: () => sh }});
    }})();

    // ─── [RULE 20] FONT LIST FINGERPRINT CLOAKING ────────────────
    (() => {{
        const allowedFonts = new Set([{font_whitelist_js}]);
        
        // 1. Hook document.fonts.check
        if (document.fonts && document.fonts.check) {{
            const origFontsCheck = document.fonts.check.bind(document.fonts);
            document.fonts.check = function(fontStr, text) {{
                if (!fontStr) return false;
                const cleaned = fontStr.replace(/^[0-9]+(px|pt|em|rem)?\\s+/, '').replace(/['"]/g, '').toLowerCase().trim();
                const fontParts = cleaned.split(',').map(s => s.trim());
                const isWhitelisted = fontParts.some(f => allowedFonts.has(f));
                if (!isWhitelisted) {{
                    return false;
                }}
                return origFontsCheck(fontStr, text);
            }};
        }}

        // 2. Cloak Canvas measureText for non-standard fonts
        const origMeasureText = CanvasRenderingContext2D.prototype.measureText;
        CanvasRenderingContext2D.prototype.measureText = function(text) {{
            const font = (this.font || '').toLowerCase();
            const metrics = origMeasureText.call(this, text);
            let isAllowed = false;
            for (const f of allowedFonts) {{
                if (font.includes(f)) {{ isAllowed = true; break; }}
            }}
            if (!isAllowed && font.length > 0) {{
                return {{
                    width: Math.round(text.length * 9.2 * 100) / 100,
                    actualBoundingBoxAscent: 10,
                    actualBoundingBoxDescent: 3,
                    actualBoundingBoxLeft: 0,
                    actualBoundingBoxRight: Math.round(text.length * 9.2 * 100) / 100
                }};
            }}
            return metrics;
        }};
    }})();

    // ─── [RULE 3] WEBRTC LEAK SHIELD ─────────────────────────────
    (() => {{
        const OrigRTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection;
        if (OrigRTCPeerConnection) {{
            const webrtcProxy = function(config) {{
                if (config && config.iceServers) {{
                    config.iceServers = config.iceServers.filter(s => !s.urls || !String(s.urls).includes('stun.'));
                }}
                const pc = new OrigRTCPeerConnection(config);
                return pc;
            }};
            webrtcProxy.prototype = OrigRTCPeerConnection.prototype;
            window.RTCPeerConnection = webrtcProxy;
            if (window.webkitRTCPeerConnection) window.webkitRTCPeerConnection = webrtcProxy;
        }}
    }})();

    // ─── [RULE 4] CANVAS 2D FINGERPRINT DETERMINISTIC NOISE ──────
    (() => {{
        const noiseSeed = {noise};
        const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function(...args) {{
            const imgData = origGetImageData.apply(this, args);
            const d = imgData.data;
            for (let i = 0; i < d.length; i += 16) {{
                const mod = Math.sin(i * noiseSeed) * 1.5;
                d[i] = Math.max(0, Math.min(255, d[i] + Math.round(mod)));
            }}
            return imgData;
        }};

        const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(...args) {{
            const ctx = this.getContext('2d');
            if (ctx) {{
                try {{
                    const img = ctx.getImageData(0, 0, Math.min(this.width, 10), Math.min(this.height, 10));
                    ctx.putImageData(img, 0, 0);
                }} catch (e) {{}}
            }}
            return origToDataURL.apply(this, args);
        }};
    }})();

    // ─── [RULE 5] WEBGL METADATA APPLE GPU SPOOFING ──────────────
    (() => {{
        const getParameterProxy = function(origFn) {{
            return function(param) {{
                if (param === 0x9245 || param === 37445) return '{vendor}';
                if (param === 0x9246 || param === 37446) return '{renderer}';
                return origFn.call(this, param);
            }};
        }};

        if (window.WebGLRenderingContext) {{
            WebGLRenderingContext.prototype.getParameter = getParameterProxy(WebGLRenderingContext.prototype.getParameter);
        }}
        if (window.WebGL2RenderingContext) {{
            WebGL2RenderingContext.prototype.getParameter = getParameterProxy(WebGL2RenderingContext.prototype.getParameter);
        }}
    }})();

    // ─── [RULE 6] AUDIOCONTEXT FFT HASH NOISE & SPOOFING ────────
    (() => {{
        const audioJitter = {profile.audio_noise_jitter};
        
        const OrigAudioBuffer = window.AudioBuffer;
        if (OrigAudioBuffer && OrigAudioBuffer.prototype.getChannelData) {{
            const origGetChannelData = OrigAudioBuffer.prototype.getChannelData;
            OrigAudioBuffer.prototype.getChannelData = function(channel) {{
                const data = origGetChannelData.call(this, channel);
                for (let i = 0; i < data.length; i += 32) {{
                    data[i] += Math.sin(i * audioJitter) * audioJitter;
                }}
                return data;
            }};

            if (OrigAudioBuffer.prototype.copyFromChannel) {{
                const origCopy = OrigAudioBuffer.prototype.copyFromChannel;
                OrigAudioBuffer.prototype.copyFromChannel = function(destination, channelNumber, startInChannel) {{
                    origCopy.call(this, destination, channelNumber, startInChannel);
                    for (let i = 0; i < destination.length; i += 32) {{
                        destination[i] += Math.sin(i * audioJitter) * audioJitter;
                    }}
                }};
            }}
        }}

        if (window.AnalyserNode) {{
            const origGetFloat = AnalyserNode.prototype.getFloatFrequencyData;
            if (origGetFloat) {{
                AnalyserNode.prototype.getFloatFrequencyData = function(array) {{
                    origGetFloat.call(this, array);
                    for (let i = 0; i < array.length; i += 16) {{
                        array[i] += Math.cos(i * audioJitter) * 0.2;
                    }}
                }};
            }}

            const origGetByte = AnalyserNode.prototype.getByteFrequencyData;
            if (origGetByte) {{
                AnalyserNode.prototype.getByteFrequencyData = function(array) {{
                    origGetByte.call(this, array);
                    for (let i = 0; i < array.length; i += 16) {{
                        const delta = Math.round(Math.sin(i * audioJitter) * 1.5);
                        array[i] = Math.max(0, Math.min(255, array[i] + delta));
                    }}
                }};
            }}
        }}
    }})();
    """

def get_chrome_cli_args(profile: BrowserProfile, user_data_dir: Optional[str] = None) -> List[str]:
    """
    Produces optimal Chromium launch arguments.
    """
    args = [
        f"--window-size={profile.viewport_width},{profile.viewport_height}",
        f"--lang={profile.accept_language}",
        "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--no-first-run",
        "--no-default-browser-check",
        "--password-store=basic",
        f"--user-agent={profile.user_agent}",
        "--enable-features=DnsOverHttps<DnsOverHttps,PostQuantumKyber",
        "--force-fieldtrials=DnsOverHttps/Enabled",
        "--dns-over-https-mode=secure",
        "--dns-over-https-templates=https://cloudflare-dns.com/dns-query",
        "--enable-quic",
        "--quic-version=h3",
        "--origin-to-force-quic-on=*"
    ]
    if profile.proxy_url:
        args.append(f"--proxy-server={profile.proxy_url}")
    return args
