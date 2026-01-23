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
