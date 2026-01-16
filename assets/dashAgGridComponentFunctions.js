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
