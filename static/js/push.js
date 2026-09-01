// ── Imagine Inventory : notifications push (PWA) + installation de l'app ──
(function(){
  if (!document.querySelector('.sidebar')) return; // pages publiques : on ne fait rien
  var STORE = 'imagine_pwa_state';
  function state(){ try { return JSON.parse(localStorage.getItem(STORE) || '{}'); } catch(e){ return {}; } }
  function setState(s){ try { localStorage.setItem(STORE, JSON.stringify(s)); } catch(e){} }
  var st = state();

  function b64ToUint8(b64){
    var padding = '='.repeat((4 - b64.length % 4) % 4);
    var raw = atob(b64.replace(/-/g,'+').replace(/_/g,'/') + padding);
    var arr = new Uint8Array(raw.length);
    for (var i=0; i<raw.length; i++) arr[i] = raw.charCodeAt(i);
    return arr;
  }

  function toast(txt, color){
    var ok = document.createElement('div');
    ok.textContent = txt;
    ok.style.cssText = 'position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:' + (color||'#16A34A') + ';color:white;padding:.8rem 1.4rem;border-radius:12px;z-index:9999;font-weight:700;box-shadow:0 8px 24px rgba(0,0,0,.25);font-size:.9rem';
    document.body.appendChild(ok);
    setTimeout(function(){ ok.remove(); }, 3500);
  }

  function enablePush(){
    return Notification.requestPermission().then(function(perm){
      if (perm !== 'granted') return;
      return navigator.serviceWorker.ready.then(function(reg){
        return fetch('/push/vapid-public').then(function(r){ return r.text(); }).then(function(vapidKey){
          vapidKey = vapidKey.trim();
          if (!vapidKey) throw new Error('pas de cle vapid');
          return reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToUint8(vapidKey) });
        }).then(function(sub){
          return fetch('/push/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subscription: sub.toJSON() })
          });
        });
      }).then(function(){
        var s = state(); s.subscribed = true; setState(s);
        toast('✅ Notifications activées !');
        var el = document.getElementById('pushPrompt'); if (el) el.remove();
      }).catch(function(e){ console.warn('push:', e); });
    });
  }

  function showPrompt(){
    if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) return;
    if (Notification.permission === 'denied') return;
    var el = document.createElement('div');
    el.id = 'pushPrompt';
    el.style.cssText = 'position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:#0B1D3A;color:white;padding:.9rem 1.2rem;border-radius:14px;box-shadow:0 8px 30px rgba(11,29,58,.4);z-index:9999;display:flex;gap:.8rem;align-items:center;max-width:92vw;width:auto';
    el.innerHTML =
      '<div style="font-size:1.6rem">🔔</div>' +
      '<div style="flex:1;min-width:0">' +
        '<div style="font-weight:800;font-size:.95rem">Activer les notifications ?</div>' +
        '<div style="font-size:.78rem;opacity:.8;margin-top:2px">Retours, rappels d\'evenements (J-3 / J-1), inventaire du jour — direct sur votre appareil.</div>' +
      '</div>' +
      '<button id="pushYes" style="background:#C41E3A;color:white;border:none;border-radius:8px;padding:.6rem 1rem;font-weight:800;cursor:pointer;white-space:nowrap">Activer</button>' +
      '<button id="pushNo" style="background:transparent;color:white;border:1px solid rgba(255,255,255,.4);border-radius:8px;padding:.6rem .9rem;cursor:pointer;white-space:nowrap">Plus tard</button>';
    document.body.appendChild(el);
    document.getElementById('pushYes').onclick = function(){
      enablePush();
      var s = state(); s.prompted = true; setState(s);
    };
    document.getElementById('pushNo').onclick = function(){
      var s = state(); s.prompted = true; setState(s);
      el.remove();
    };
  }

  // ── Bandeau "Installer l'app" (avantinstallprompt = Chrome/Android/Edge) ──
  window.addEventListener('beforeinstallprompt', function(e){
    e.preventDefault();
    var deferred = e;
    var s = state();
    if (s.installed) return;
    var el = document.createElement('div');
    el.id = 'installPrompt';
    el.style.cssText = 'position:fixed;top:12px;right:12px;z-index:9999;background:white;border:2px solid #0B1D3A;border-radius:14px;box-shadow:0 8px 30px rgba(11,29,58,.25);padding:.8rem 1rem;display:flex;gap:.7rem;align-items:center;max-width:330px';
    el.innerHTML =
      '<div style="font-size:1.5rem">📲</div>' +
      '<div style="flex:1;min-width:0">' +
        '<div style="font-weight:800;font-size:.85rem;color:#0B1D3A">Installer l\'app</div>' +
        '<div style="font-size:.72rem;color:#64748B">Imagine Inventory sur votre ecran d\'accueil</div>' +
      '</div>' +
      '<button id="installYes" style="background:#0B1D3A;color:white;border:none;border-radius:8px;padding:.55rem .9rem;font-weight:800;cursor:pointer">Installer</button>' +
      '<button id="installNo" style="background:none;border:none;color:#94A3B8;cursor:pointer;font-size:1.1rem">✕</button>';
    document.body.appendChild(el);
    document.getElementById('installYes').onclick = function(){
      deferred.prompt();
      deferred.userChoice.then(function(){
        var s2 = state(); s2.installed = true; setState(s2);
        var x = document.getElementById('installPrompt'); if (x) x.remove();
      });
    };
    document.getElementById('installNo').onclick = function(){
      var s2 = state(); s2.installed = true; setState(s2);
      el.remove();
    };
  });
  window.addEventListener('appinstalled', function(){
    var s = state(); s.installed = true; setState(s);
    var x = document.getElementById('installPrompt'); if (x) x.remove();
  });

  // ── Init : si permission deja donnee -> abonnement silencieux, sinon bandeau ──
  function init(){
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
    if (st.subscribed && Notification.permission === 'granted') return; // deja ok
    if (Notification.permission === 'granted') {
      enablePush();
    } else if (!st.prompted) {
      // Bandeau propose UNE seule fois (1ere visite)
      setTimeout(function(){
        var s = state(); s.prompted = true; setState(s);
        showPrompt();
      }, 4000);
    }
  }
  if (document.readyState === 'complete') init();
  else window.addEventListener('load', init);
})();
