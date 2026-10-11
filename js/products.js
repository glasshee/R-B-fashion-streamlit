const PRODUCT_CATALOG = [
	{
		id: 'baggy-blue-denim',
		name: 'Baggy blue denim',
		category: 'Denim',
		price: 320,
		pages: ['new', 'all', 'men'],
		images: [
			'https://images.unsplash.com/photo-1628196871136-a6e5fc060309?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1552374196-c4e7ffc6e126?auto=format&fit=crop&w=900&q=80'
		]
	},
	{
		id: 'baggy-cargo-denim',
		name: 'Baggy cargo denim',
		category: 'Denim',
		price: 360,
		pages: ['new', 'women'],
		images: [
			'https://images.unsplash.com/photo-1628196871136-a6e5fc060309?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1542272604-787c3835535d?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1539109136881-3be0616acf4b?auto=format&fit=crop&w=900&q=80'
		]
	},
	{
		id: 'oversized-graphic-tee',
		name: 'Oversized graphic tee',
		category: 'Streetwear',
		price: 240,
		pages: ['new', 'all', 'men'],
		images: [
			'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1485968579580-b6d095142e6e?auto=format&fit=crop&w=900&q=80'
		]
	},
	{
		id: 'oversized-campus-fit',
		name: 'Oversized campus fit',
		category: 'Streetwear',
		price: 390,
		pages: ['new', 'all'],
		images: [
			'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1485968579580-b6d095142e6e?auto=format&fit=crop&w=900&q=80'
		]
	},
	{
		id: 'asics-gel-street-runners',
		name: 'ASICS GEL street runners',
		category: 'Sneakers',
		price: 720,
		pages: ['new', 'all', 'shoes'],
		images: [
			'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?auto=format&fit=crop&w=900&q=80'
		]
	},
	{
		id: 'platform-street-sneakers',
		name: 'Platform street sneakers',
		category: 'Sneakers',
		price: 590,
		pages: ['shoes'],
		images: [
			'https://images.unsplash.com/photo-1600185365483-26d7a4cc7519?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?auto=format&fit=crop&w=900&q=80'
		]
	},
	{
		id: 'dr-martens-street-boots',
		name: 'Dr. Martens street boots',
		category: 'Boots',
		price: 780,
		pages: ['all', 'shoes'],
		images: [
			'https://images.unsplash.com/photo-1608256246200-53e635b5b65f?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=900&q=80'
		]
	},
	{
		id: 'clean-white-low-tops',
		name: 'Clean white low-tops',
		category: 'Sneakers',
		price: 490,
		pages: ['shoes'],
		images: [
			'https://images.unsplash.com/photo-1628196871136-a6e5fc060309?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80'
		]
	},
	{
		id: 'oversized-varsity-hoodie',
		name: 'Oversized varsity hoodie',
		category: 'Layers',
		price: 410,
		pages: ['women'],
		images: [
			'https://images.unsplash.com/photo-1551488831-00ddcb6c6bd3?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=900&q=80'
		]
	},
	{
		id: 'tailored-black-suit',
		name: 'Tailored black suit',
		category: 'Formal',
		price: 950,
		pages: ['formal', 'men'],
		images: [
			'https://images.unsplash.com/photo-1618886614638-80e3c103d31a?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=900&q=80'
		]
	},
	{
		id: 'satin-evening-dress',
		name: 'Satin evening dress',
		category: 'Formal',
		price: 820,
		pages: ['formal', 'women'],
		images: [
			'https://images.unsplash.com/photo-1531123897727-8f129e1688ce?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1595777457583-95e059d581b8?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1496747611176-843222e1e57c?auto=format&fit=crop&w=900&q=80'
		]
	},
	{
		id: 'clean-cut-formal-shirt',
		name: 'Clean cut formal shirt',
		category: 'Formal',
		price: 360,
		pages: ['formal'],
		images: [
			'https://images.unsplash.com/photo-1618886614638-80e3c103d31a?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=900&q=80',
			'https://images.unsplash.com/photo-1594938298603-c8148c4dae35?auto=format&fit=crop&w=900&q=80'
		]
	}
];
