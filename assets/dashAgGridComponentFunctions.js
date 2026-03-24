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

// Cell renderer for game name with year and ID as subtext
dagcomponentfuncs.GameInfo = function(props) {
    if (!props.value) return null;
    var data = props.data;
    var gameId = data.game_id;
    var year = data.year_published;
    var url = 'https://boardgamegeek.com/boardgame/' + gameId;

    return React.createElement('div', { style: { padding: '6px 0', lineHeight: '1.3', wordBreak: 'break-word' } },
        React.createElement('a', {
            href: url,
            target: '_blank',
            rel: 'noopener noreferrer',
            style: { color: '#e2e8f0', textDecoration: 'none', fontWeight: '600', fontSize: '0.95em' }
        }, props.value),
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
