const suitMapping = {
    'c': { symbol: '♣', color: 'limegreen' },
    'd': { symbol: '♦', color: 'dodgerblue' },
    'h': { symbol: '♥', color: 'red' },
    's': { symbol: '♠', color: 'darkgray' },
};

function formatCard(card) {
    const rank = card.slice(0, -1);
    const suit = card.slice(-1);

    if (suit in suitMapping) {
        const { symbol, color } = suitMapping[suit];
        const formattedCard = `<span style="color: ${color};">${rank}${symbol}</span>`;
        return formattedCard;
    } else {
        return "Invalid card";
    }
}
