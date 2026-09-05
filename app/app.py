"""Dash application factory — no external stylesheets, no dash-bootstrap-components.

Cloned from Spin Rate. The panel is warmed here at import so the one-time (~0.6s)
generation happens at process boot, never on a visitor's first request.
"""

import os
import secrets

import dash

from app import panel_data

app = dash.Dash(
    __name__,
    assets_folder="../assets",
    suppress_callback_exceptions=True,
    title="Decompose — Which Lever Moved Sales",
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {
            "name": "description",
            "content": (
                "Splits a period-over-period sales change into buying households, "
                "purchase frequency, and spend per trip, reconciled to the exact delta."
            ),
        },
        {"property": "og:title", "content": "Decompose: Which Lever Moved Sales"},
        {
            "property": "og:description",
            "content": (
                "Splits a period-over-period sales change into buying households, "
                "purchase frequency, and spend per trip, reconciled to the exact delta."
            ),
        },
        {"property": "og:type", "content": "website"},
        {"property": "og:url", "content": "https://decompose.lailarallc.com/"},
        {"property": "og:image", "content": "https://lailarallc.com/og/s/decompose.png"},
        {
            "property": "og:image:secure_url",
            "content": "https://lailarallc.com/og/s/decompose.png",
        },
        {"property": "og:image:type", "content": "image/png"},
        {"property": "og:image:width", "content": "1200"},
        {"property": "og:image:height", "content": "630"},
        {"property": "og:image:alt", "content": "Decompose: Which Lever Moved Sales"},
        {"name": "twitter:card", "content": "summary_large_image"},
        {"name": "twitter:image", "content": "https://lailarallc.com/og/s/decompose.png"},
    ],
)
server = app.server
server.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

# Build the in-process panel once, at startup (see panel_data.warm_cache).
panel_data.warm_cache()

# ── Branded loading overlay ──────────────────────────────────────────
# Decompose is sent to prospects as a cold link, so the first hydration (Dash
# renderer boot + the default view's data callback) leaves a blank white screen for
# a beat. That reads as broken.
#
# This overlay is plain static HTML/CSS injected directly into the page body, so the
# browser paints it on the *first frame* — before any Dash JavaScript runs. It does
# NOT depend on the Dash renderer being ready (that would defeat the purpose). A
# small inline script watches the DOM for the rendered tab navigation and fades the
# overlay out the moment the shell is interactive.
#
# Colors/fonts are literal Lailara tokens (not CSS variables) so the overlay is
# styled even before the external stylesheet finishes loading.
_LOADING_OVERLAY = """
    <style>
      #decompose-loading {
        position: fixed;
        inset: 0;
        z-index: 99999;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #f5f3ee; /* Canvas — London-100 warmed */
        transition: opacity 300ms ease-out;
      }
      #decompose-loading.dc-hide { opacity: 0; pointer-events: none; }
      .dc-load-inner { text-align: center; padding: 0 24px; }
      .dc-load-spinner {
        width: 46px;
        height: 46px;
        margin: 0 auto 26px;
        border: 3px solid #d9d9d9;     /* London-85 gridline */
        border-top-color: #1f2e7a;     /* Chicago-20 navy */
        border-radius: 50%;
        animation: dc-spin 900ms linear infinite;
      }
      .dc-load-brand {
        font-family: 'Playfair Display', Georgia, 'Times New Roman', serif;
        font-size: 26px;              /* DS Brand-name step; 20px mobile below */
        font-weight: 700;
        color: #0d0d0d;                /* Ink */
        letter-spacing: -0.01em;
        line-height: 1.2;
      }
      .dc-load-sub {
        font-family: 'Source Sans 3', 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 12px;
        font-weight: 600;
        color: #595959;                /* Text secondary */
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 10px;
      }
      .dc-load-hint {
        font-family: 'Source Sans 3', 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 14px;
        font-weight: 400;
        color: #595959;                /* Text secondary */
        margin-top: 22px;
      }
      @keyframes dc-spin { to { transform: rotate(360deg); } }
      @media (prefers-reduced-motion: reduce) {
        #decompose-loading { transition: none; }
        .dc-load-spinner {
          animation: none;
          border-color: #1f2e7a;       /* full navy ring, no motion */
        }
      }
      @media (max-width: 640px) {
        .dc-load-brand { font-size: 20px; }
      }
    </style>
    <div id="decompose-loading" role="status" aria-live="polite" aria-label="Loading Decompose">
      <div class="dc-load-inner">
        <div class="dc-load-spinner" aria-hidden="true"></div>
        <div class="dc-load-brand">Decompose</div>
        <div class="dc-load-sub">Penetration &times; Three Levers</div>
        <div class="dc-load-hint">Preparing the decomposition&hellip;</div>
      </div>
    </div>
    <script>
      (function () {
        var SAFETY_MS = 20000;
        function hide() {
          var el = document.getElementById('decompose-loading');
          if (!el || el.classList.contains('dc-hide')) return;
          el.classList.add('dc-hide');
          setTimeout(function () {
            if (el && el.parentNode) el.parentNode.removeChild(el);
          }, 400);
        }
        // The default tab is interactive once Plotly has drawn the waterfall (its
        // data callback has returned). If the chart never paints, the SAFETY_MS
        // timeout below hides the overlay anyway, so the visitor is never trapped.
        function ready() {
          return !!document.querySelector('#waterfall-chart .js-plotly-plot');
        }
        function check() {
          if (ready()) { hide(); return true; }
          return false;
        }
        if (check()) return;
        var obs = new MutationObserver(function () {
          if (check()) obs.disconnect();
        });
        obs.observe(document.documentElement, { childList: true, subtree: true });
        // Never trap the visitor behind the overlay if the shell never paints.
        setTimeout(function () { obs.disconnect(); hide(); }, SAFETY_MS);
      })();
    </script>
"""

app.index_string = """<!DOCTYPE html>
<html lang="en">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        __LOADING_OVERLAY__
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>""".replace("__LOADING_OVERLAY__", _LOADING_OVERLAY)
