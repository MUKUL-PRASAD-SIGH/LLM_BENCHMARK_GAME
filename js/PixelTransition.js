// PixelTransition React Component
// Converted from React PixelCard to work with vanilla JS + React CDN

class Pixel {
    constructor(canvas, ctx, x, y, color, speed, delay) {
        this.width = canvas.width;
        this.height = canvas.height;
        this.ctx = ctx;
        this.x = x;
        this.y = y;
        this.color = color;
        this.speed = (Math.random() * 0.8 + 0.1) * speed;
        this.size = 0;
        this.sizeStep = Math.random() * 0.4 + 0.1;
        this.minSize = 0.5;
        this.maxSizeInteger = 4;
        this.maxSize = Math.random() * (this.maxSizeInteger - this.minSize) + this.minSize;
        this.delay = delay;
        this.counter = 0;
        this.counterStep = Math.random() * 4 + (this.width + this.height) * 0.01;
        this.isIdle = false;
        this.isReverse = false;
        this.isShimmer = false;
    }

    draw() {
        const centerOffset = this.maxSizeInteger * 0.5 - this.size * 0.5;
        this.ctx.fillStyle = this.color;
        this.ctx.fillRect(this.x + centerOffset, this.y + centerOffset, this.size, this.size);
    }

    appear() {
        this.isIdle = false;
        if (this.counter <= this.delay) {
            this.counter += this.counterStep;
            return;
        }
        if (this.size >= this.maxSize) {
            this.isShimmer = true;
        }
        if (this.isShimmer) {
            this.shimmer();
        } else {
            this.size += this.sizeStep;
        }
        this.draw();
    }

    disappear() {
        this.isShimmer = false;
        this.counter = 0;
        if (this.size <= 0) {
            this.isIdle = true;
            return;
        } else {
            this.size -= 0.15;
        }
        this.draw();
    }

    shimmer() {
        if (this.size >= this.maxSize) {
            this.isReverse = true;
        } else if (this.size <= this.minSize) {
            this.isReverse = false;
        }
        if (this.isReverse) {
            this.size -= this.speed;
        } else {
            this.size += this.speed;
        }
    }
}

// React Component using hooks
const PixelTransition = ({ isActive, onComplete, text = "FIGHT!" }) => {
    const canvasRef = React.useRef(null);
    const pixelsRef = React.useRef([]);
    const animationRef = React.useRef(null);
    const hasCompletedRef = React.useRef(false);
    const [showText, setShowText] = React.useState(false);

    const colors = ['#1e90ff', '#0ea5e9', '#7dd3fc', '#ff0040', '#ffcc00', '#00ff00', '#ff6b6b', '#fbbf24'];
    const gap = 8;
    const speed = 0.035;

    const initPixels = React.useCallback(() => {
        if (!canvasRef.current) return;

        const canvas = canvasRef.current;
        const width = window.innerWidth;
        const height = window.innerHeight;
        const ctx = canvas.getContext('2d');

        canvas.width = width;
        canvas.height = height;

        const pxs = [];
        for (let x = 0; x < width; x += gap) {
            for (let y = 0; y < height; y += gap) {
                const color = colors[Math.floor(Math.random() * colors.length)];
                const dx = x - width / 2;
                const dy = y - height / 2;
                const distance = Math.sqrt(dx * dx + dy * dy);
                pxs.push(new Pixel(canvas, ctx, x, y, color, speed, distance * 0.3));
            }
        }
        pixelsRef.current = pxs;
    }, []);

    const animateAppear = React.useCallback(() => {
        if (!canvasRef.current) return;

        const ctx = canvasRef.current.getContext('2d');
        ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);

        for (let i = 0; i < pixelsRef.current.length; i++) {
            pixelsRef.current[i].appear();
        }

        animationRef.current = requestAnimationFrame(animateAppear);
    }, []);

    const animateDisappear = React.useCallback(() => {
        if (!canvasRef.current) return;

        const ctx = canvasRef.current.getContext('2d');
        ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);

        let allIdle = true;
        for (let i = 0; i < pixelsRef.current.length; i++) {
            pixelsRef.current[i].disappear();
            if (!pixelsRef.current[i].isIdle) {
                allIdle = false;
            }
        }

        if (allIdle && !hasCompletedRef.current) {
            hasCompletedRef.current = true;
            cancelAnimationFrame(animationRef.current);
            if (onComplete) onComplete();
            return;
        }

        animationRef.current = requestAnimationFrame(animateDisappear);
    }, [onComplete]);

    React.useEffect(() => {
        if (isActive && !hasCompletedRef.current) {
            initPixels();
            animateAppear();

            // Show text after pixels start filling
            const textTimer = setTimeout(() => {
                setShowText(true);
            }, 600);

            // Start disappearing and navigate
            const disappearTimer = setTimeout(() => {
                setShowText(false);
                cancelAnimationFrame(animationRef.current);
                pixelsRef.current.forEach(p => {
                    p.isIdle = false;
                    p.isShimmer = false;
                });
                animateDisappear();
            }, 1800);

            // Safety fallback - ensure navigation happens
            const fallbackTimer = setTimeout(() => {
                if (!hasCompletedRef.current) {
                    hasCompletedRef.current = true;
                    cancelAnimationFrame(animationRef.current);
                    if (onComplete) onComplete();
                }
            }, 3500);

            return () => {
                clearTimeout(textTimer);
                clearTimeout(disappearTimer);
                clearTimeout(fallbackTimer);
                cancelAnimationFrame(animationRef.current);
            };
        }
    }, [isActive, initPixels, animateAppear, animateDisappear, onComplete]);

    if (!isActive) return null;

    return React.createElement('div', {
        className: 'pixel-transition-overlay active'
    }, [
        React.createElement('canvas', {
            key: 'canvas',
            ref: canvasRef,
            className: 'pixel-canvas'
        }),
        React.createElement('div', {
            key: 'text',
            className: `transition-text ${showText ? 'show' : ''}`
        }, text)
    ]);
};

// Export for use
window.PixelTransition = PixelTransition;
window.Pixel = Pixel;
