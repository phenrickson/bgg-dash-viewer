// Custom cell renderers for Dash AG Grid

var dagcomponentfuncs = window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {};

// Cell renderer for external links that open in new tab
dagcomponentfuncs.ExternalLink = function(props) {
    if (!props.value) return null;

    const gameId = props.data.game_id;
    const url = `https://boardgamegeek.com/boardgame/${gameId}`;

    return React.createElement(
        'a',
        {
            href: url,
            target: '_blank',
            rel: 'noopener noreferrer',
            style: { color: 'var(--bs-link-color)' }
        },
        props.value
    );
};

// Cell renderer for thumbnail images
dagcomponentfuncs.ThumbnailImage = function(props) {
    if (!props.value) return null;

    return React.createElement(
        'img',
        {
            src: props.value,
            style: {
                height: '40px',
                width: '40px',
                objectFit: 'cover',
                borderRadius: '4px'
            }
        }
    );
};

// Cell renderer for combined player counts (best highlighted, recommended secondary)
dagcomponentfuncs.PlayerCountPills = function(props) {
    const data = props.data;
    if (!data) return null;

    const bestStr = data.best_player_counts || '';
    const recStr = data.recommended_player_counts || '';

    // Parse counts
    const bestCounts = new Set(bestStr.split(',').map(s => s.trim()).filter(s => s));
    const recCounts = recStr.split(',').map(s => s.trim()).filter(s => s);

    // Get all unique counts, sorted
    const allCounts = [...new Set([...bestCounts, ...recCounts])]
        .filter(s => s)
        .sort((a, b) => parseInt(a) - parseInt(b));

    if (allCounts.length === 0) return null;

    const containerStyle = {
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '3px',
        height: '100%',
        width: '100%'
    };

    return React.createElement(
        'div',
        { style: containerStyle },
        allCounts.map((count, i) =>
            React.createElement('span', {
                key: i,
                className: bestCounts.has(count) ? 'badge bg-success' : 'badge bg-secondary'
            }, count)
        )
    );
};

// Cell renderer for numeric values with colored text based on value range
dagcomponentfuncs.ColoredNumber = function(props) {
    if (props.value == null) return null;
    var v = parseFloat(props.value);
    var p = props.colDef.cellRendererParams || {};
    var min = p.min || 0;
    var max = p.max || 10;
    var decimals = p.decimals != null ? p.decimals : 2;
    var hue = p.hue != null ? p.hue : 210;
    // Use a power curve to spread out differences at the high end
    var t = Math.max(0, Math.min(1, (v - min) / (max - min)));
    t = Math.pow(t, 0.4);
    var minSat = p.minSat != null ? p.minSat : 10;
    var minLight = p.minLight != null ? p.minLight : 35;
    var s = Math.round(minSat + t * (90 - minSat));
    var l = Math.round(minLight + t * (75 - minLight));
    return React.createElement('div', {
        style: { textAlign: 'center', fontWeight: '600', color: 'hsl(' + hue + ',' + s + '%,' + l + '%)' }
    }, v.toFixed(decimals));
};

// Cell renderer for complexity: light blue (low) → white (mid) → red (high)
dagcomponentfuncs.ComplexityNumber = function(props) {
    if (props.value == null) return null;
    var v = parseFloat(props.value);
    var t = Math.max(0, Math.min(1, (v - 1.0) / (5.0 - 1.0)));
    var r, g, b;
    if (t <= 0.5) {
        // Light blue to white
        var s = t / 0.5;
        r = Math.round(130 + s * 125);
        g = Math.round(190 + s * 65);
        b = Math.round(235 + s * 20);
    } else {
        // White to red
        var s = (t - 0.5) / 0.5;
        r = Math.round(255 - s * 35);
        g = Math.round(255 - s * 175);
        b = Math.round(255 - s * 185);
    }
    return React.createElement('div', {
        style: { textAlign: 'center', fontWeight: '600', color: 'rgb(' + r + ',' + g + ',' + b + ')' }
    }, v.toFixed(2));
};

// Cell renderer for rating values as a colored pill badge
dagcomponentfuncs.RatingBadge = function(props) {
    if (props.value == null) return null;
    var v = parseFloat(props.value);
    var params = props.colDef.cellRendererParams || {};
    var min = params.min || 0;
    var max = params.max || 10;
    var decimals = params.decimals != null ? params.decimals : 2;
    var t = Math.max(0, Math.min(1, (v - min) / (max - min)));

    // Color interpolation from muted to vibrant
    var r = Math.round(156 - t * 100);
    var g = Math.round(163 + t * 60);
    var b = Math.round(175 - t * 30);
    var bgOpacity = 0.15 + t * 0.2;

    return React.createElement('div', { style: { display: 'flex', justifyContent: 'center', padding: '6px 0' } },
        React.createElement('span', {
            style: {
                backgroundColor: 'rgba(' + r + ',' + g + ',' + b + ',' + bgOpacity + ')',
                color: 'rgb(' + r + ',' + g + ',' + b + ')',
                padding: '4px 12px',
                borderRadius: '6px',
                fontSize: '0.85em',
                fontWeight: '600',
                minWidth: '48px',
                textAlign: 'center',
                display: 'inline-block'
            }
        }, v.toFixed(decimals))
    );
};

// Cell renderer for playtime as a badge
dagcomponentfuncs.PlaytimeBadge = function(props) {
    var data = props.data;
    if (!data) return null;
    var minTime = data.min_playtime;
    var maxTime = data.max_playtime;
    if (minTime == null && maxTime == null) return null;

    var label;
    if (minTime === maxTime) {
        label = (minTime || '-') + 'm';
    } else {
        label = (minTime || '?') + '\u2013' + (maxTime || '?') + 'm';
    }

    return React.createElement('div', {
        style: { display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', width: '100%' }
    },
        React.createElement('span', {
            className: 'badge bg-secondary',
            style: { fontWeight: '500', fontSize: '0.85em', color: '#e5e7eb' }
        }, label)
    );
};

// Cell renderer for game name with year and ID as subtext
dagcomponentfuncs.GameInfo = function(props) {
    if (!props.value) return null;
    var data = props.data;
    var gameId = data.game_id;
    var year = data.year_published;
    var isNew = data.is_new_7d;
    var url = 'https://boardgamegeek.com/boardgame/' + gameId;

    var nameChildren = [];
    if (isNew) {
        nameChildren.push(React.createElement('span', {
            key: 'badge',
            style: { backgroundColor: '#065f46', color: '#6ee7b7', padding: '1px 6px', borderRadius: '3px', fontSize: '0.7em', fontWeight: '600', marginRight: '6px', verticalAlign: 'middle' }
        }, 'NEW'));
    }
    nameChildren.push(React.createElement('a', {
        key: 'link',
        href: url,
        target: '_blank',
        rel: 'noopener noreferrer',
        style: { color: '#e2e8f0', textDecoration: 'none', fontWeight: '600', fontSize: '0.95em' }
    }, props.value));

    return React.createElement('div', { style: { padding: '6px 0', lineHeight: '1.3', wordBreak: 'break-word' } },
        React.createElement('div', null, nameChildren),
        React.createElement('div', {
            style: { fontSize: '0.75em', color: '#9ca3af', marginTop: '2px' }
        }, (year ? year + ' · ' : '') + gameId)
    );
};

// Cell renderer for date with time as subtext
dagcomponentfuncs.DateTimeStacked = function(props) {
    var data = props.data;
    if (!data) return null;
    var date = data.load_date || '';
    var time = data.load_time || '';

    return React.createElement('div', { style: { padding: '6px 0', lineHeight: '1.3' } },
        React.createElement('div', { style: { fontSize: '0.85em' } }, date),
        React.createElement('div', { style: { fontSize: '0.75em', color: '#9ca3af' } }, time)
    );
};

// Cell renderer for comma-separated values displayed as badges with expand/collapse
dagcomponentfuncs.BadgeList = function(props) {
    if (!props.value) return null;

    var items = props.value.split(',').map(function(s) { return s.trim(); }).filter(function(s) { return s; });
    if (items.length === 0) return null;

    var maxVisible = props.colDef.cellRendererParams && props.colDef.cellRendererParams.maxVisible || 3;
    var badgeColor = props.colDef.cellRendererParams && props.colDef.cellRendererParams.badgeColor || '#6c757d';

    var expanded = React.useState(false);
    var isExpanded = expanded[0];
    var setExpanded = expanded[1];

    var visibleItems = isExpanded ? items : items.slice(0, maxVisible);
    var hiddenCount = items.length - maxVisible;

    var containerStyle = {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        gap: '3px',
        padding: '6px 0'
    };

    var badgeStyle = {
        backgroundColor: '#374151',
        color: '#e5e7eb',
        padding: '3px 8px',
        borderRadius: '4px',
        fontSize: '0.75em',
        fontWeight: 'normal',
        lineHeight: '1.4'
    };

    var children = visibleItems.map(function(item, i) {
        return React.createElement('span', { key: i, style: badgeStyle }, item);
    });

    if (hiddenCount > 0 && !isExpanded) {
        children.push(React.createElement('span', {
            key: 'more',
            style: {
                color: '#9ca3af',
                fontSize: '0.75em',
                cursor: 'pointer',
                padding: '2px 0'
            },
            onClick: function() { setExpanded(true); }
        }, '+' + hiddenCount + ' more'));
    } else if (isExpanded && hiddenCount > 0) {
        children.push(React.createElement('span', {
            key: 'less',
            style: {
                color: '#9ca3af',
                fontSize: '0.75em',
                cursor: 'pointer',
                padding: '2px 0'
            },
            onClick: function() { setExpanded(false); }
        }, 'show less'));
    }

    return React.createElement('div', { style: containerStyle }, children);
};
