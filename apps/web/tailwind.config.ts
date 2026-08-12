import type { Config } from "tailwindcss";

export default {
	content: ["./index.html", "./src/**/*.{ts,tsx}"],
	theme: {
		extend: {
			colors: {
				brand: {
					DEFAULT: "#0E7C7B",
					dark: "#075E5D",
					light: "#34D1BF",
				},
			},
			fontFamily: {
				sans: [
					"Outfit",
					"ui-sans-serif",
					"system-ui",
					"sans-serif",
				],
				display: [
					"Fraunces",
					"Georgia",
					"ui-serif",
					"serif",
				],
			},
		},
	},
	plugins: [],
} satisfies Config;
