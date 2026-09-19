const { useState, useEffect, useCallback, createContext, useContext } = React;

const API_BASE = '/app/api';

const TITLE_COLORS = {
    title_vip: { color: '#ffd23c', bg: 'rgba(255,210,60,0.15)' },
    title_legend: { color: '#ffb432', bg: 'rgba(255,180,50,0.15)' },
    title_whale: { color: '#50c8ff', bg: 'rgba(80,200,255,0.15)' },
    title_god: { color: '#b478ff', bg: 'rgba(180,120,255,0.15)' },
    title_owner: { color: '#ff5050', bg: 'rgba(255,80,80,0.15)' },
    title_ket: { color: '#64ffc8', bg: 'rgba(100,255,200,0.15)' },
};

const AuthContext = createContext(null);

function useAuth() {
    return useContext(AuthContext);
}

function api(path, options = {}) {
    const token = localStorage.getItem('webapp_token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    return fetch(`${API_BASE}${path}`, { ...options, headers: { ...headers, ...options.headers } })
        .then(async r => {
            const data = await r.json();
            if (!r.ok) throw new Error(data.error || 'request failed');
            return data;
        });
}

function formatNumber(n) {
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

function calcLevel(totalGames, wins, totalBet) {
    if (totalGames < 10) return { name: 'NEWBIE', color: '#8c82af', filled: 0 };
    const winrate = totalGames > 0 ? wins / totalGames : 0;
    const score = winrate * 100 + Math.log10(totalBet + 1) * 10;
    if (score > 120) return { name: 'DIAMOND', color: '#b4e6ff', filled: 3 };
    if (score > 90) return { name: 'GOLD', color: '#ffd23c', filled: 3 };
    if (score > 60) return { name: 'SILVER', color: '#c0c0c0', filled: 2 };
    return { name: 'BRONZE', color: '#cd7f32', filled: 1 };
}

// --- Components ---

function Loading() {
    return (
        <div className="loading">
            <div className="spinner" />
            Загрузка...
        </div>
    );
}

function Toast({ message, type }) {
    if (!message) return null;
    return <div className={`toast ${type}`}>{message}</div>;
}

function Stars({ filled }) {
    return (
        <div className="stars">
            {[1, 2, 3].map(i => (
                <span key={i} className={`star ${i <= filled ? 'filled' : 'empty'}`}>★</span>
            ))}
        </div>
    );
}

function NavBar({ page, onNavigate }) {
    const items = [
        { id: 'profile', icon: '👤', label: 'Профиль' },
        { id: 'games', icon: '🎮', label: 'Игры' },
        { id: 'shop', icon: '🛒', label: 'Магазин' },
        { id: 'ref', icon: '👥', label: 'Рефералы' },
    ];
    return (
        <nav className="nav-bar">
            {items.map(it => (
                <button
                    key={it.id}
                    className={`nav-item ${page === it.id ? 'active' : ''}`}
                    onClick={() => onNavigate(it.id)}
                >
                    <span className="nav-icon">{it.icon}</span>
                    {it.label}
                </button>
            ))}
        </nav>
    );
}

function ProfilePage({ profile }) {
    if (!profile) return <Loading />;
    const level = calcLevel(profile.total_games, profile.wins, profile.total_bet);
    const winrate = profile.total_games > 0
        ? ((profile.wins / profile.total_games) * 100).toFixed(1)
        : '0.0';
    const titleInfo = profile.active_title ? TITLE_COLORS[profile.active_title] : null;
    const titleNames = {
        title_vip: 'VIP', title_legend: 'LEGEND', title_whale: 'WHALE',
        title_god: 'GOD', title_owner: 'OWNER', title_ket: 'KET',
    };
    const initials = (profile.first_name || 'K')[0].toUpperCase();

    return (
        <div>
            <div className="profile-header">
                <div className="avatar">{initials}</div>
                <div className="profile-info">
                    <div className="profile-name">{profile.first_name || 'Игрок'}</div>
                    <div className="profile-id">ID: {profile.user_id}</div>
                    {profile.active_title && titleInfo && (
                        <div
                            className="profile-title-banner"
                            style={{
                                color: titleInfo.color,
                                background: titleInfo.bg,
                                border: `1px solid ${titleInfo.color}40`,
                            }}
                        >
                            {titleNames[profile.active_title] || profile.active_title}
                        </div>
                    )}
                    <Stars filled={level.filled} />
                </div>
            </div>

            <div className="card">
                <div className="balance-row">
                    <div className="balance-item">
                        <div className="balance-label">Баланс</div>
                        <div className="balance-value ton">{formatNumber(profile.balance)}</div>
                        <div className="balance-unit">TON</div>
                    </div>
                    <div className="balance-item">
                        <div className="balance-label">Рубины</div>
                        <div className="balance-value ruby">{formatNumber(Math.floor(profile.rubies))}</div>
                        <div className="balance-unit">GEMS</div>
                    </div>
                </div>
            </div>

            <div className="card">
                <div className="card-title">Статистика</div>
                <div className="stat-row">
                    <span className="stat-label">Игр</span>
                    <span className="stat-value">{formatNumber(profile.total_games)}</span>
                </div>
                <div className="stat-row">
                    <span className="stat-label">Побед</span>
                    <span className="stat-value green">{formatNumber(profile.wins)}</span>
                </div>
                <div className="stat-row">
                    <span className="stat-label">Поражений</span>
                    <span className="stat-value red">{formatNumber(profile.losses)}</span>
                </div>
                <div className="winrate-container">
                    <div className="winrate-header">
                        <span className="stat-label">Винрейт</span>
                        <span className="stat-value gold">{winrate}%</span>
                    </div>
                    <div className="winrate-bar">
                        <div className="winrate-fill" style={{ width: `${winrate}%` }} />
                    </div>
                </div>
                <div className="stat-row">
                    <span className="stat-label">Общие ставки</span>
                    <span className="stat-value">{formatNumber(profile.total_bet)}</span>
                </div>
                <div className="stat-row">
                    <span className="stat-label">Общий выигрыш</span>
                    <span className="stat-value green">{formatNumber(profile.total_won)}</span>
                </div>
                <div className="stat-row">
                    <span className="stat-label">Рефералы</span>
                    <span className="stat-value">{profile.referral_count}</span>
                </div>
            </div>
        </div>
    );
}

function GamesPage() {
    const games = [
        { icon: '💣', name: 'Мины', desc: '5×5 поле с минами', coming: true },
        { icon: '🃏', name: 'Джокер', desc: 'Отгадай дверь', coming: true },
        { icon: '⚗️', name: 'Алхимик', desc: 'Смешай зелья', coming: true },
        { icon: '🪙', name: 'Монетка', desc: 'Орёл или решка', coming: true },
    ];
    return (
        <div>
            <div className="section-title">🎮 Игры</div>
            <div className="card" style={{ textAlign: 'center', padding: '30px 20px' }}>
                <p style={{ color: 'var(--text-dim)', marginBottom: '8px' }}>
                    Игры скоро будут доступны в WebApp!
                </p>
                <p style={{ fontSize: '13px', color: 'var(--text-dim)' }}>
                    Пока что играйте через бота — нажмите "🎮 Игры" в меню бота.
                </p>
            </div>
            <div className="games-grid">
                {games.map(g => (
                    <div key={g.name} className="game-card" style={{ opacity: 0.5 }}>
                        <div className="game-icon">{g.icon}</div>
                        <div className="game-name">{g.name}</div>
                        <div className="game-desc">{g.desc}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function ShopPage({ profile, refreshProfile }) {
    const [shop, setShop] = useState(null);
    const [toast, setToast] = useState(null);

    useEffect(() => {
        api('/shop').then(setShop).catch(() => {});
    }, []);

    const showToast = (msg, type = 'success') => {
        setToast({ message: msg, type });
        setTimeout(() => setToast(null), 3000);
    };

    const buy = async (itemId) => {
        try {
            const res = await api('/shop/buy', {
                method: 'POST',
                body: JSON.stringify({ item_id: itemId }),
            });
            showToast('Покупка успешна!');
            setShop(s => ({ ...s, balance: res.balance }));
            refreshProfile();
            // Mark as owned in local state
            setShop(s => {
                if (!s) return s;
                const update = items => items.map(i =>
                    i.id === itemId ? { ...i, owned: true } : i
                );
                return { ...s, frames: update(s.frames), titles: update(s.titles) };
            });
        } catch (e) {
            if (e.message === 'insufficient balance') showToast('Недостаточно TON', 'error');
            else if (e.message === 'already owned') showToast('Уже куплено', 'error');
            else showToast('Ошибка', 'error');
        }
    };

    const equip = async (itemId, category) => {
        try {
            await api('/shop/equip', {
                method: 'POST',
                body: JSON.stringify({ item_id: itemId }),
            });
            showToast('Экипировано!');
            refreshProfile();
            setShop(s => {
                if (!s) return s;
                const update = (items, cat) => items.map(i =>
                    i.category === cat ? { ...i, active: i.id === itemId } : { ...i, active: false }
                );
                return s;
            });
        } catch (e) {
            showToast('Ошибка', 'error');
        }
    };

    const unequip = async (category) => {
        try {
            await api('/shop/equip', {
                method: 'POST',
                body: JSON.stringify({ item_id: '', category }),
            });
            showToast('Снято');
            refreshProfile();
        } catch (e) {
            showToast('Ошибка', 'error');
        }
    };

    if (!shop) return <Loading />;

    return (
        <div>
            <Toast {...toast} />
            <div className="section-title">🛒 Магазин</div>
            <div className="card">
                <div className="balance-row">
                    <div className="balance-item">
                        <div className="balance-label">Баланс</div>
                        <div className="balance-value ton">{formatNumber(shop.balance)}</div>
                        <div className="balance-unit">TON</div>
                    </div>
                </div>
            </div>

            <div className="card">
                <div className="card-title">🖼 Рамки профиля</div>
                <div className="shop-category">
                    {shop.frames.map(f => (
                        <div
                            key={f.id}
                            className={`shop-card ${f.active ? 'active' : ''}`}
                            style={{ borderColor: f.active ? `rgb(${f.color.join(',')})` : undefined }}
                        >
                            <div className="item-name" style={{ color: `rgb(${f.color.join(',')})` }}>{f.name}</div>
                            {f.owned ? (
                                <>
                                    <div className="item-owned">✓ Куплено</div>
                                    {f.active ? (
                                        <button className="btn-unequip" onClick={() => unequip('frame')}>Снять</button>
                                    ) : (
                                        <button className="btn btn-small btn-primary" style={{ marginTop: 8 }} onClick={() => equip(f.id)}>Экипировать</button>
                                    )}
                                </>
                            ) : (
                                <div className="item-price">{formatNumber(f.price)} TON</div>
                            )}
                            {!f.owned && (
                                <button className="btn btn-small btn-gold" style={{ marginTop: 8 }} onClick={() => buy(f.id)}>Купить</button>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            <div className="card">
                <div className="card-title">🏷 Титулы</div>
                <div className="shop-category">
                    {shop.titles.map(t => {
                        const tc = TITLE_COLORS[t.id] || { color: '#ffd23c', bg: 'rgba(255,210,60,0.15)' };
                        return (
                            <div
                                key={t.id}
                                className={`shop-card ${t.active ? 'active' : ''}`}
                            >
                                <div className="item-name" style={{ color: tc.color }}>{t.name}</div>
                                {t.owned ? (
                                    <>
                                        <div className="item-owned">✓ Куплено</div>
                                        {t.active ? (
                                            <button className="btn-unequip" onClick={() => unequip('title')}>Снять</button>
                                        ) : (
                                            <button className="btn btn-small btn-primary" style={{ marginTop: 8 }} onClick={() => equip(t.id)}>Экипировать</button>
                                        )}
                                    </>
                                ) : (
                                    <div className="item-price">{formatNumber(t.price)} TON</div>
                                )}
                                {!t.owned && (
                                    <button className="btn btn-small btn-gold" style={{ marginTop: 8 }} onClick={() => buy(t.id)}>Купить</button>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}

function ReferralPage({ profile }) {
    const botUsername = 'tonbotgram_bot';
    const refLink = `https://t.me/${botUsername}?start=ref${profile?.user_id || ''}`;
    const [copied, setCopied] = useState(false);

    const copyLink = () => {
        navigator.clipboard.writeText(refLink).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    return (
        <div>
            <div className="section-title">👥 Рефералы</div>
            <div className="card">
                <div className="card-title">Ваша ссылка</div>
                <div className="ref-link">{refLink}</div>
                <button className="btn btn-primary" onClick={copyLink}>
                    {copied ? '✓ Скопировано!' : '📋 Копировать ссылку'}
                </button>
            </div>
            <div className="card">
                <div className="card-title">Статистика</div>
                <div className="ref-stats">
                    <div className="balance-item">
                        <div className="balance-label">Рефералов</div>
                        <div className="balance-value" style={{ color: 'var(--cyan)' }}>
                            {profile?.referral_count || 0}
                        </div>
                    </div>
                    <div className="balance-item">
                        <div className="balance-label">Бонус</div>
                        <div className="balance-value" style={{ color: 'var(--green)' }}>
                            5%
                        </div>
                    </div>
                </div>
                <p style={{ marginTop: 12, fontSize: '13px', color: 'var(--text-dim)' }}>
                    Получайте 5% от ставок каждого приглашённого игрока.
                </p>
            </div>
        </div>
    );
}

function AuthScreen({ onAuth }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(false);

    useEffect(() => {
        const tg = window.Telegram?.WebApp;
        const data = tg?.initData || tg?.initDataUnsafe;
        if (data) {
            setLoading(true);
            onAuth(data);
        } else {
            setError(true);
        }
    }, []);

    const handleAuth = () => {
        setLoading(true);
        const tg = window.Telegram?.WebApp;
        const data = tg?.initData || tg?.initDataUnsafe;
        if (data) {
            onAuth(data);
        } else {
            setLoading(false);
            setError(true);
        }
    };

    return (
        <div className="auth-screen">
            <div className="logo">🎰</div>
            <h2>TON Casino</h2>
            <p>Играй и зарабатывай</p>
            {loading ? (
                <p style={{ color: 'var(--purple)' }}>Вход...</p>
            ) : error ? (
                <>
                    <p style={{ color: 'var(--red)', marginBottom: 16 }}>
                        Откройте приложение из бота
                    </p>
                    <button className="btn btn-primary" onClick={handleAuth}>
                        Попробовать снова
                    </button>
                </>
            ) : (
                <button className="btn btn-primary" onClick={handleAuth}>
                    Войти через Telegram
                </button>
            )}
        </div>
    );
}

function App() {
    const [user, setUser] = useState(null);
    const [profile, setProfile] = useState(null);
    const [page, setPage] = useState('profile');
    const [loading, setLoading] = useState(true);

    const refreshProfile = useCallback(() => {
        if (!user) return;
        api('/profile').then(setProfile).catch(() => {});
    }, [user]);

    useEffect(() => {
        const token = localStorage.getItem('webapp_token');
        if (token) {
            try {
                const payload = JSON.parse(token);
                setUser(payload);
                api('/profile').then(p => {
                    setProfile(p);
                    setLoading(false);
                }).catch(() => {
                    localStorage.removeItem('webapp_token');
                    setLoading(false);
                });
            } catch {
                localStorage.removeItem('webapp_token');
                setLoading(false);
            }
        } else {
            setLoading(false);
        }

        // Telegram WebApp init
        if (window.Telegram?.WebApp) {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }
    }, []);

    const handleAuth = async (initData) => {
        try {
            const res = await fetch(`${API_BASE}/auth`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ initData }),
            });
            const data = await res.json();
            if (data.token) {
                localStorage.setItem('webapp_token', data.token);
                setUser({ user_id: data.user_id });
                api('/profile').then(setProfile);
            } else {
                console.error('Auth failed:', data);
            }
        } catch (e) {
            console.error('Auth error:', e);
        }
    };

    if (loading) return <Loading />;
    if (!user) return <AuthScreen onAuth={handleAuth} />;

    return (
        <div className="app">
            <div className="header">
                <h1>TON Casino</h1>
                <div className="subtitle">Играй и зарабатывай</div>
            </div>

            {page === 'profile' && <ProfilePage profile={profile} />}
            {page === 'games' && <GamesPage />}
            {page === 'shop' && <ShopPage profile={profile} refreshProfile={refreshProfile} />}
            {page === 'ref' && <ReferralPage profile={profile} />}

            <NavBar page={page} onNavigate={setPage} />
        </div>
    );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
