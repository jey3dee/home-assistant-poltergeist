// node_modules/@lit/reactive-element/css-tag.js
var e = globalThis, t = e.ShadowRoot && (e.ShadyCSS === void 0 || e.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype, n = Symbol(), r = /* @__PURE__ */ new WeakMap(), i = class {
	constructor(e, t, r) {
		if (this._$cssResult$ = !0, r !== n) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
		this.cssText = e, this.t = t;
	}
	get styleSheet() {
		let e = this.o, n = this.t;
		if (t && e === void 0) {
			let t = n !== void 0 && n.length === 1;
			t && (e = r.get(n)), e === void 0 && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), t && r.set(n, e));
		}
		return e;
	}
	toString() {
		return this.cssText;
	}
}, a = (e) => new i(typeof e == "string" ? e : e + "", void 0, n), o = (e, ...t) => new i(e.length === 1 ? e[0] : t.reduce((t, n, r) => t + ((e) => {
	if (!0 === e._$cssResult$) return e.cssText;
	if (typeof e == "number") return e;
	throw Error("Value passed to 'css' function must be a 'css' function result: " + e + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
})(n) + e[r + 1], e[0]), e, n), s = (n, r) => {
	if (t) n.adoptedStyleSheets = r.map((e) => e instanceof CSSStyleSheet ? e : e.styleSheet);
	else for (let t of r) {
		let r = document.createElement("style"), i = e.litNonce;
		i !== void 0 && r.setAttribute("nonce", i), r.textContent = t.cssText, n.appendChild(r);
	}
}, c = t ? (e) => e : (e) => e instanceof CSSStyleSheet ? ((e) => {
	let t = "";
	for (let n of e.cssRules) t += n.cssText;
	return a(t);
})(e) : e, { is: l, defineProperty: u, getOwnPropertyDescriptor: d, getOwnPropertyNames: ee, getOwnPropertySymbols: te, getPrototypeOf: ne } = Object, f = globalThis, p = f.trustedTypes, re = p ? p.emptyScript : "", ie = f.reactiveElementPolyfillSupport, m = (e, t) => e, h = {
	toAttribute(e, t) {
		switch (t) {
			case Boolean:
				e = e ? re : null;
				break;
			case Object:
			case Array: e = e == null ? e : JSON.stringify(e);
		}
		return e;
	},
	fromAttribute(e, t) {
		let n = e;
		switch (t) {
			case Boolean:
				n = e !== null;
				break;
			case Number:
				n = e === null ? null : Number(e);
				break;
			case Object:
			case Array: try {
				n = JSON.parse(e);
			} catch {
				n = null;
			}
		}
		return n;
	}
}, g = (e, t) => !l(e, t), _ = {
	attribute: !0,
	type: String,
	converter: h,
	reflect: !1,
	useDefault: !1,
	hasChanged: g
};
Symbol.metadata ??= Symbol("metadata"), f.litPropertyMetadata ??= /* @__PURE__ */ new WeakMap();
var v = class extends HTMLElement {
	static addInitializer(e) {
		this._$Ei(), (this.l ??= []).push(e);
	}
	static get observedAttributes() {
		return this.finalize(), this._$Eh && [...this._$Eh.keys()];
	}
	static createProperty(e, t = _) {
		if (t.state && (t.attribute = !1), this._$Ei(), this.prototype.hasOwnProperty(e) && ((t = Object.create(t)).wrapped = !0), this.elementProperties.set(e, t), !t.noAccessor) {
			let n = Symbol(), r = this.getPropertyDescriptor(e, n, t);
			r !== void 0 && u(this.prototype, e, r);
		}
	}
	static getPropertyDescriptor(e, t, n) {
		let { get: r, set: i } = d(this.prototype, e) ?? {
			get() {
				return this[t];
			},
			set(e) {
				this[t] = e;
			}
		};
		return {
			get: r,
			set(t) {
				let a = r?.call(this);
				i?.call(this, t), this.requestUpdate(e, a, n);
			},
			configurable: !0,
			enumerable: !0
		};
	}
	static getPropertyOptions(e) {
		return this.elementProperties.get(e) ?? _;
	}
	static _$Ei() {
		if (this.hasOwnProperty(m("elementProperties"))) return;
		let e = ne(this);
		e.finalize(), e.l !== void 0 && (this.l = [...e.l]), this.elementProperties = new Map(e.elementProperties);
	}
	static finalize() {
		if (this.hasOwnProperty(m("finalized"))) return;
		if (this.finalized = !0, this._$Ei(), this.hasOwnProperty(m("properties"))) {
			let e = this.properties, t = [...ee(e), ...te(e)];
			for (let n of t) this.createProperty(n, e[n]);
		}
		let e = this[Symbol.metadata];
		if (e !== null) {
			let t = litPropertyMetadata.get(e);
			if (t !== void 0) for (let [e, n] of t) this.elementProperties.set(e, n);
		}
		this._$Eh = /* @__PURE__ */ new Map();
		for (let [e, t] of this.elementProperties) {
			let n = this._$Eu(e, t);
			n !== void 0 && this._$Eh.set(n, e);
		}
		this.elementStyles = this.finalizeStyles(this.styles);
	}
	static finalizeStyles(e) {
		let t = [];
		if (Array.isArray(e)) {
			let n = new Set(e.flat(1 / 0).reverse());
			for (let e of n) t.unshift(c(e));
		} else e !== void 0 && t.push(c(e));
		return t;
	}
	static _$Eu(e, t) {
		let n = t.attribute;
		return !1 === n ? void 0 : typeof n == "string" ? n : typeof e == "string" ? e.toLowerCase() : void 0;
	}
	constructor() {
		super(), this._$Ep = void 0, this.isUpdatePending = !1, this.hasUpdated = !1, this._$Em = null, this._$Ev();
	}
	_$Ev() {
		this._$ES = new Promise((e) => this.enableUpdating = e), this._$AL = /* @__PURE__ */ new Map(), this._$E_(), this.requestUpdate(), this.constructor.l?.forEach((e) => e(this));
	}
	addController(e) {
		(this._$EO ??= /* @__PURE__ */ new Set()).add(e), this.renderRoot !== void 0 && this.isConnected && e.hostConnected?.();
	}
	removeController(e) {
		this._$EO?.delete(e);
	}
	_$E_() {
		let e = /* @__PURE__ */ new Map(), t = this.constructor.elementProperties;
		for (let n of t.keys()) this.hasOwnProperty(n) && (e.set(n, this[n]), delete this[n]);
		e.size > 0 && (this._$Ep = e);
	}
	createRenderRoot() {
		let e = this.shadowRoot ?? this.attachShadow(this.constructor.shadowRootOptions);
		return s(e, this.constructor.elementStyles), e;
	}
	connectedCallback() {
		this.renderRoot ??= this.createRenderRoot(), this.enableUpdating(!0), this._$EO?.forEach((e) => e.hostConnected?.());
	}
	enableUpdating(e) {}
	disconnectedCallback() {
		this._$EO?.forEach((e) => e.hostDisconnected?.());
	}
	attributeChangedCallback(e, t, n) {
		this._$AK(e, n);
	}
	_$ET(e, t) {
		let n = this.constructor.elementProperties.get(e), r = this.constructor._$Eu(e, n);
		if (r !== void 0 && !0 === n.reflect) {
			let i = (n.converter?.toAttribute === void 0 ? h : n.converter).toAttribute(t, n.type);
			this._$Em = e, i == null ? this.removeAttribute(r) : this.setAttribute(r, i), this._$Em = null;
		}
	}
	_$AK(e, t) {
		let n = this.constructor, r = n._$Eh.get(e);
		if (r !== void 0 && this._$Em !== r) {
			let e = n.getPropertyOptions(r), i = typeof e.converter == "function" ? { fromAttribute: e.converter } : e.converter?.fromAttribute === void 0 ? h : e.converter;
			this._$Em = r;
			let a = i.fromAttribute(t, e.type);
			this[r] = a ?? this._$Ej?.get(r) ?? a, this._$Em = null;
		}
	}
	requestUpdate(e, t, n, r = !1, i) {
		if (e !== void 0) {
			let a = this.constructor;
			if (!1 === r && (i = this[e]), n ??= a.getPropertyOptions(e), !((n.hasChanged ?? g)(i, t) || n.useDefault && n.reflect && i === this._$Ej?.get(e) && !this.hasAttribute(a._$Eu(e, n)))) return;
			this.C(e, t, n);
		}
		!1 === this.isUpdatePending && (this._$ES = this._$EP());
	}
	C(e, t, { useDefault: n, reflect: r, wrapped: i }, a) {
		n && !(this._$Ej ??= /* @__PURE__ */ new Map()).has(e) && (this._$Ej.set(e, a ?? t ?? this[e]), !0 !== i || a !== void 0) || (this._$AL.has(e) || (this.hasUpdated || n || (t = void 0), this._$AL.set(e, t)), !0 === r && this._$Em !== e && (this._$Eq ??= /* @__PURE__ */ new Set()).add(e));
	}
	async _$EP() {
		this.isUpdatePending = !0;
		try {
			await this._$ES;
		} catch (e) {
			Promise.reject(e);
		}
		let e = this.scheduleUpdate();
		return e != null && await e, !this.isUpdatePending;
	}
	scheduleUpdate() {
		return this.performUpdate();
	}
	performUpdate() {
		if (!this.isUpdatePending) return;
		if (!this.hasUpdated) {
			if (this.renderRoot ??= this.createRenderRoot(), this._$Ep) {
				for (let [e, t] of this._$Ep) this[e] = t;
				this._$Ep = void 0;
			}
			let e = this.constructor.elementProperties;
			if (e.size > 0) for (let [t, n] of e) {
				let { wrapped: e } = n, r = this[t];
				!0 !== e || this._$AL.has(t) || r === void 0 || this.C(t, void 0, n, r);
			}
		}
		let e = !1, t = this._$AL;
		try {
			e = this.shouldUpdate(t), e ? (this.willUpdate(t), this._$EO?.forEach((e) => e.hostUpdate?.()), this.update(t)) : this._$EM();
		} catch (t) {
			throw e = !1, this._$EM(), t;
		}
		e && this._$AE(t);
	}
	willUpdate(e) {}
	_$AE(e) {
		this._$EO?.forEach((e) => e.hostUpdated?.()), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
	}
	_$EM() {
		this._$AL = /* @__PURE__ */ new Map(), this.isUpdatePending = !1;
	}
	get updateComplete() {
		return this.getUpdateComplete();
	}
	getUpdateComplete() {
		return this._$ES;
	}
	shouldUpdate(e) {
		return !0;
	}
	update(e) {
		this._$Eq &&= this._$Eq.forEach((e) => this._$ET(e, this[e])), this._$EM();
	}
	updated(e) {}
	firstUpdated(e) {}
};
v.elementStyles = [], v.shadowRootOptions = { mode: "open" }, v[m("elementProperties")] = /* @__PURE__ */ new Map(), v[m("finalized")] = /* @__PURE__ */ new Map(), ie?.({ ReactiveElement: v }), (f.reactiveElementVersions ??= []).push("2.1.2");
// node_modules/lit-html/lit-html.js
var y = globalThis, ae = (e) => e, b = y.trustedTypes, oe = b ? b.createPolicy("lit-html", { createHTML: (e) => e }) : void 0, x = "$lit$", S = `lit$${Math.random().toFixed(9).slice(2)}$`, C = "?" + S, se = `<${C}>`, w = document, T = () => w.createComment(""), E = (e) => e === null || typeof e != "object" && typeof e != "function", D = Array.isArray, O = (e) => D(e) || typeof e?.[Symbol.iterator] == "function", k = "[ 	\n\f\r]", A = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g, ce = /-->/g, le = />/g, j = RegExp(`>|${k}(?:([^\\s"'>=/]+)(${k}*=${k}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`, "g"), M = /'/g, N = /"/g, P = /^(?:script|style|textarea|title)$/i, F = ((e) => (t, ...n) => ({
	_$litType$: e,
	strings: t,
	values: n
}))(1), I = Symbol.for("lit-noChange"), L = Symbol.for("lit-nothing"), R = /* @__PURE__ */ new WeakMap(), z = w.createTreeWalker(w, 129);
function B(e, t) {
	if (!D(e) || !e.hasOwnProperty("raw")) throw Error("invalid template strings array");
	return oe === void 0 ? t : oe.createHTML(t);
}
var V = (e, t) => {
	let n = e.length - 1, r = [], i, a = t === 2 ? "<svg>" : t === 3 ? "<math>" : "", o = A;
	for (let t = 0; t < n; t++) {
		let n = e[t], s, c, l = -1, u = 0;
		for (; u < n.length && (o.lastIndex = u, c = o.exec(n), c !== null);) u = o.lastIndex, o === A ? c[1] === "!--" ? o = ce : c[1] === void 0 ? c[2] === void 0 ? c[3] !== void 0 && (o = j) : (P.test(c[2]) && (i = RegExp("</" + c[2], "g")), o = j) : o = le : o === j ? c[0] === ">" ? (o = i ?? A, l = -1) : c[1] === void 0 ? l = -2 : (l = o.lastIndex - c[2].length, s = c[1], o = c[3] === void 0 ? j : c[3] === "\"" ? N : M) : o === N || o === M ? o = j : o === ce || o === le ? o = A : (o = j, i = void 0);
		let d = o === j && e[t + 1].startsWith("/>") ? " " : "";
		a += o === A ? n + se : l >= 0 ? (r.push(s), n.slice(0, l) + x + n.slice(l) + S + d) : n + S + (l === -2 ? t : d);
	}
	return [B(e, a + (e[n] || "<?>") + (t === 2 ? "</svg>" : t === 3 ? "</math>" : "")), r];
}, H = class e {
	constructor({ strings: t, _$litType$: n }, r) {
		let i;
		this.parts = [];
		let a = 0, o = 0, s = t.length - 1, c = this.parts, [l, u] = V(t, n);
		if (this.el = e.createElement(l, r), z.currentNode = this.el.content, n === 2 || n === 3) {
			let e = this.el.content.firstChild;
			e.replaceWith(...e.childNodes);
		}
		for (; (i = z.nextNode()) !== null && c.length < s;) {
			if (i.nodeType === 1) {
				if (i.hasAttributes()) for (let e of i.getAttributeNames()) if (e.endsWith(x)) {
					let t = u[o++], n = i.getAttribute(e).split(S), r = /([.?@])?(.*)/.exec(t);
					c.push({
						type: 1,
						index: a,
						name: r[2],
						strings: n,
						ctor: r[1] === "." ? q : r[1] === "?" ? J : r[1] === "@" ? Y : K
					}), i.removeAttribute(e);
				} else e.startsWith(S) && (c.push({
					type: 6,
					index: a
				}), i.removeAttribute(e));
				if (P.test(i.tagName)) {
					let e = i.textContent.split(S), t = e.length - 1;
					if (t > 0) {
						i.textContent = b ? b.emptyScript : "";
						for (let n = 0; n < t; n++) i.append(e[n], T()), z.nextNode(), c.push({
							type: 2,
							index: ++a
						});
						i.append(e[t], T());
					}
				}
			} else if (i.nodeType === 8) {
				if (i.data === C) c.push({
					type: 2,
					index: a
				});
				else {
					let e = -1;
					for (; (e = i.data.indexOf(S, e + 1)) !== -1;) c.push({
						type: 7,
						index: a
					}), e += S.length - 1;
				}
			}
			a++;
		}
	}
	static createElement(e, t) {
		let n = w.createElement("template");
		return n.innerHTML = e, n;
	}
};
function U(e, t, n = e, r) {
	if (t === I) return t;
	let i = r === void 0 ? n._$Cl : n._$Co?.[r], a = E(t) ? void 0 : t._$litDirective$;
	return i?.constructor !== a && (i?._$AO?.(!1), a === void 0 ? i = void 0 : (i = new a(e), i._$AT(e, n, r)), r === void 0 ? n._$Cl = i : (n._$Co ??= [])[r] = i), i !== void 0 && (t = U(e, i._$AS(e, t.values), i, r)), t;
}
var W = class {
	constructor(e, t) {
		this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
	}
	get parentNode() {
		return this._$AM.parentNode;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	u(e) {
		let { el: { content: t }, parts: n } = this._$AD, r = (e?.creationScope ?? w).importNode(t, !0);
		z.currentNode = r;
		let i = z.nextNode(), a = 0, o = 0, s = n[0];
		for (; s !== void 0;) {
			if (a === s.index) {
				let t;
				s.type === 2 ? t = new G(i, i.nextSibling, this, e) : s.type === 1 ? t = new s.ctor(i, s.name, s.strings, this, e) : s.type === 6 && (t = new ue(i, this, e)), this._$AV.push(t), s = n[++o];
			}
			a !== s?.index && (i = z.nextNode(), a++);
		}
		return z.currentNode = w, r;
	}
	p(e) {
		let t = 0;
		for (let n of this._$AV) n !== void 0 && (n.strings === void 0 ? n._$AI(e[t]) : (n._$AI(e, n, t), t += n.strings.length - 2)), t++;
	}
}, G = class e {
	get _$AU() {
		return this._$AM?._$AU ?? this._$Cv;
	}
	constructor(e, t, n, r) {
		this.type = 2, this._$AH = L, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = n, this.options = r, this._$Cv = r?.isConnected ?? !0;
	}
	get parentNode() {
		let e = this._$AA.parentNode, t = this._$AM;
		return t !== void 0 && e?.nodeType === 11 && (e = t.parentNode), e;
	}
	get startNode() {
		return this._$AA;
	}
	get endNode() {
		return this._$AB;
	}
	_$AI(e, t = this) {
		e = U(this, e, t), E(e) ? e === L || e == null || e === "" ? (this._$AH !== L && this._$AR(), this._$AH = L) : e !== this._$AH && e !== I && this._(e) : e._$litType$ === void 0 ? e.nodeType === void 0 ? O(e) ? this.k(e) : this._(e) : this.T(e) : this.$(e);
	}
	O(e) {
		return this._$AA.parentNode.insertBefore(e, this._$AB);
	}
	T(e) {
		this._$AH !== e && (this._$AR(), this._$AH = this.O(e));
	}
	_(e) {
		this._$AH !== L && E(this._$AH) ? this._$AA.nextSibling.data = e : this.T(w.createTextNode(e)), this._$AH = e;
	}
	$(e) {
		let { values: t, _$litType$: n } = e, r = typeof n == "number" ? this._$AC(e) : (n.el === void 0 && (n.el = H.createElement(B(n.h, n.h[0]), this.options)), n);
		if (this._$AH?._$AD === r) this._$AH.p(t);
		else {
			let e = new W(r, this), n = e.u(this.options);
			e.p(t), this.T(n), this._$AH = e;
		}
	}
	_$AC(e) {
		let t = R.get(e.strings);
		return t === void 0 && R.set(e.strings, t = new H(e)), t;
	}
	k(t) {
		D(this._$AH) || (this._$AH = [], this._$AR());
		let n = this._$AH, r, i = 0;
		for (let a of t) i === n.length ? n.push(r = new e(this.O(T()), this.O(T()), this, this.options)) : r = n[i], r._$AI(a), i++;
		i < n.length && (this._$AR(r && r._$AB.nextSibling, i), n.length = i);
	}
	_$AR(e = this._$AA.nextSibling, t) {
		for (this._$AP?.(!1, !0, t); e !== this._$AB;) {
			let t = ae(e).nextSibling;
			ae(e).remove(), e = t;
		}
	}
	setConnected(e) {
		this._$AM === void 0 && (this._$Cv = e, this._$AP?.(e));
	}
}, K = class {
	get tagName() {
		return this.element.tagName;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	constructor(e, t, n, r, i) {
		this.type = 1, this._$AH = L, this._$AN = void 0, this.element = e, this.name = t, this._$AM = r, this.options = i, n.length > 2 || n[0] !== "" || n[1] !== "" ? (this._$AH = Array(n.length - 1).fill(/* @__PURE__ */ new String()), this.strings = n) : this._$AH = L;
	}
	_$AI(e, t = this, n, r) {
		let i = this.strings, a = !1;
		if (i === void 0) e = U(this, e, t, 0), a = !E(e) || e !== this._$AH && e !== I, a && (this._$AH = e);
		else {
			let r = e, o, s;
			for (e = i[0], o = 0; o < i.length - 1; o++) s = U(this, r[n + o], t, o), s === I && (s = this._$AH[o]), a ||= !E(s) || s !== this._$AH[o], s === L ? e = L : e !== L && (e += (s ?? "") + i[o + 1]), this._$AH[o] = s;
		}
		a && !r && this.j(e);
	}
	j(e) {
		e === L ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, e ?? "");
	}
}, q = class extends K {
	constructor() {
		super(...arguments), this.type = 3;
	}
	j(e) {
		this.element[this.name] = e === L ? void 0 : e;
	}
}, J = class extends K {
	constructor() {
		super(...arguments), this.type = 4;
	}
	j(e) {
		this.element.toggleAttribute(this.name, !!e && e !== L);
	}
}, Y = class extends K {
	constructor(e, t, n, r, i) {
		super(e, t, n, r, i), this.type = 5;
	}
	_$AI(e, t = this) {
		if ((e = U(this, e, t, 0) ?? L) === I) return;
		let n = this._$AH, r = e === L && n !== L || e.capture !== n.capture || e.once !== n.once || e.passive !== n.passive, i = e !== L && (n === L || r);
		r && this.element.removeEventListener(this.name, this, n), i && this.element.addEventListener(this.name, this, e), this._$AH = e;
	}
	handleEvent(e) {
		typeof this._$AH == "function" ? this._$AH.call(this.options?.host ?? this.element, e) : this._$AH.handleEvent(e);
	}
}, ue = class {
	constructor(e, t, n) {
		this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = n;
	}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AI(e) {
		U(this, e);
	}
}, de = {
	M: x,
	P: S,
	A: C,
	C: 1,
	L: V,
	R: W,
	D: O,
	V: U,
	I: G,
	H: K,
	N: J,
	U: Y,
	B: q,
	F: ue
}, fe = y.litHtmlPolyfillSupport;
fe?.(H, G), (y.litHtmlVersions ??= []).push("3.3.3");
var pe = (e, t, n) => {
	let r = n?.renderBefore ?? t, i = r._$litPart$;
	if (i === void 0) {
		let e = n?.renderBefore ?? null;
		r._$litPart$ = i = new G(t.insertBefore(T(), e), e, void 0, n ?? {});
	}
	return i._$AI(e), i;
}, X = globalThis, Z = class extends v {
	constructor() {
		super(...arguments), this.renderOptions = { host: this }, this._$Do = void 0;
	}
	createRenderRoot() {
		let e = super.createRenderRoot();
		return this.renderOptions.renderBefore ??= e.firstChild, e;
	}
	update(e) {
		let t = this.render();
		this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = pe(t, this.renderRoot, this.renderOptions);
	}
	connectedCallback() {
		super.connectedCallback(), this._$Do?.setConnected(!0);
	}
	disconnectedCallback() {
		super.disconnectedCallback(), this._$Do?.setConnected(!1);
	}
	render() {
		return I;
	}
};
Z._$litElement$ = !0, Z.finalized = !0, X.litElementHydrateSupport?.({ LitElement: Z });
var me = X.litElementPolyfillSupport;
me?.({ LitElement: Z }), (X.litElementVersions ??= []).push("4.2.2");
// src/format.ts
function he(e) {
	return e > 0 && e < 1 ? "< 1 %" : `${Math.round(e)} %`;
}
function ge(e) {
	return e.toFixed(2);
}
// node_modules/lit-html/directive.js
var Q = {
	ATTRIBUTE: 1,
	CHILD: 2,
	PROPERTY: 3,
	BOOLEAN_ATTRIBUTE: 4,
	EVENT: 5,
	ELEMENT: 6
}, _e = (e) => (...t) => ({
	_$litDirective$: e,
	values: t
}), ve = class {
	constructor(e) {}
	get _$AU() {
		return this._$AM._$AU;
	}
	_$AT(e, t, n) {
		this._$Ct = e, this._$AM = t, this._$Ci = n;
	}
	_$AS(e, t) {
		return this.update(e, t);
	}
	update(e, t) {
		return this.render(...t);
	}
}, { I: ye } = de, be = (e) => e.strings === void 0, xe = {}, Se = (e, t = xe) => e._$AH = t, Ce = _e(class extends ve {
	constructor(e) {
		if (super(e), e.type !== Q.PROPERTY && e.type !== Q.ATTRIBUTE && e.type !== Q.BOOLEAN_ATTRIBUTE) throw Error("The `live` directive is not allowed on child or event bindings");
		if (!be(e)) throw Error("`live` bindings can only contain a single expression");
	}
	render(e) {
		return e;
	}
	update(e, [t]) {
		if (t === I || t === L) return t;
		let n = e.element, r = e.name;
		if (e.type === Q.PROPERTY) {
			if (t === n[r]) return I;
		} else if (e.type === Q.BOOLEAN_ATTRIBUTE) {
			if (!!t === n.hasAttribute(r)) return I;
		} else if (e.type === Q.ATTRIBUTE && n.getAttribute(r) === t + "") return I;
		return Se(e), t;
	}
}), we = 1e3, Te = 8, $ = (e) => {
	let t = e;
	return t.code ?? t.message ?? "unknown error";
}, Ee = class extends Z {
	static properties = {
		hass: { attribute: !1 },
		_data: { state: !0 },
		_error: { state: !0 },
		_addSensor: { state: !0 },
		_addRoom: { state: !0 }
	};
	_started = !1;
	constructor() {
		super(), this._addSensor = "", this._addRoom = "";
	}
	willUpdate(e) {
		e.has("hass") && this.hass && !this._started && (this._started = !0, this._load());
	}
	async _load() {
		for (let e = 1; e <= Te; e++) try {
			this._data = await this.hass.callWS({ type: "poltergeist/sensors" }), this._error = void 0;
			return;
		} catch (t) {
			if (t.code !== "not_loaded" || e === Te) {
				this._error = $(t);
				return;
			}
			await new Promise((e) => setTimeout(e, we));
		}
	}
	async _assign(e, t) {
		this._error = void 0;
		try {
			await this.hass.callWS({
				type: "poltergeist/assign",
				entity_id: e,
				area_id: t
			});
		} catch (e) {
			this._error = $(e), await this._load(), this._error = $(e);
			return;
		}
		let n = this._data, r = n.sensors.some((t) => t.entity_id === e), i = n.candidates.find((t) => t.entity_id === e);
		this._data = {
			...n,
			sensors: r ? n.sensors.map((n) => n.entity_id === e ? {
				...n,
				room: t
			} : n) : [...n.sensors, this._rowFor(i, t)].sort((e, t) => e.entity_id.localeCompare(t.entity_id)),
			candidates: n.candidates.filter((t) => t.entity_id !== e)
		};
	}
	_rowFor(e, t) {
		return {
			entity_id: e.entity_id,
			name: e.name,
			device_class: null,
			ha_area_id: e.ha_area_id,
			room: t
		};
	}
	async _add() {
		await this._assign(this._addSensor, this._addRoom), this._addSensor = "", this._addRoom = "";
	}
	async _restore() {
		if (window.confirm("Forget every change you made and use the areas of Home Assistant for all sensors?")) {
			this._error = void 0;
			try {
				await this.hass.callWS({ type: "poltergeist/restore_proposals" });
			} catch (e) {
				this._error = $(e);
				return;
			}
			await this._load();
		}
	}
	render() {
		if (this._error && !this._data) return F`<p class="note error">Could not load the sensors: ${this._error}</p>`;
		let e = this._data;
		if (!e) return F`<p class="note">Loading…</p>`;
		let t = (t) => e.rooms.find((e) => e.area_id === t)?.name ?? "none", n = new Set(e.sensors.map((e) => e.room)), r = e.rooms.filter((e) => !n.has(e.area_id));
		return F`
      ${this._error ? F`<p class="note error">${this._error}</p>` : L}
      <table>
        <thead>
          <tr>
            <th>Sensor</th>
            <th>Class</th>
            <th>State</th>
            <th>Room</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${e.sensors.map((n) => F`<tr>
              <td>${n.name}<div class="id">${n.entity_id}</div></td>
              <td>${n.device_class ?? ""}</td>
              <td data-state>${this.hass?.states[n.entity_id]?.state ?? ""}</td>
              <td>
                <select
                  aria-label="Room of ${n.name}"
                  @change=${(e) => this._assign(n.entity_id, e.target.value || null)}
                >
                  <option value="" .selected=${Ce(n.room === null)}>No room</option>
                  ${e.rooms.map((e) => F`<option
                        value=${e.area_id}
                        .selected=${Ce(n.room === e.area_id)}
                      >
                        ${e.name}
                      </option>`)}
                </select>
              </td>
              <td class="marker">
                ${n.room === n.ha_area_id ? "as proposed" : F`changed<span class="id">
                        (Home Assistant: ${t(n.ha_area_id)})</span
                      >`}
              </td>
            </tr>`)}
        </tbody>
      </table>
      <div class="actions">
        <select
          data-add-sensor
          aria-label="Sensor to add"
          @change=${(e) => this._addSensor = e.target.value}
        >
          <option value="">Add a sensor…</option>
          ${e.candidates.map((e) => F`<option value=${e.entity_id}>${e.name} (${e.entity_id})</option>`)}
        </select>
        <select
          data-add-room
          aria-label="Room for the new sensor"
          @change=${(e) => this._addRoom = e.target.value}
        >
          <option value="">in room…</option>
          ${e.rooms.map((e) => F`<option value=${e.area_id}>${e.name}</option>`)}
        </select>
        <button data-add ?disabled=${!this._addSensor || !this._addRoom} @click=${this._add}>
          Add
        </button>
        <button data-restore @click=${this._restore}>Restore proposals</button>
      </div>
      ${r.length ? F`<p class="note">
            Rooms without sensors: ${r.map((e) => e.name).join(", ")}
          </p>` : L}
    `;
	}
	static styles = o`
    :host {
      display: block;
      padding: 16px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: var(--card-background-color, #fff);
      border-radius: 12px;
      overflow: hidden;
    }
    th,
    td {
      text-align: left;
      padding: 8px 12px;
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
    }
    th {
      color: var(--secondary-text-color);
      font-weight: 500;
    }
    .id {
      color: var(--secondary-text-color);
      font-size: 12px;
    }
    .marker {
      color: var(--secondary-text-color);
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 16px 0;
    }
    select,
    button {
      font: inherit;
      padding: 6px 10px;
    }
    .note {
      color: var(--secondary-text-color);
    }
    .error {
      color: var(--error-color);
    }
  `;
};
customElements.define("poltergeist-sensors", Ee);
// src/panel.ts
var De = "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z", Oe = [
	"Overview",
	"Map",
	"People",
	"Sensors",
	"Health"
], ke = class extends Z {
	static properties = {
		hass: { attribute: !1 },
		narrow: { type: Boolean },
		_rooms: { state: !0 },
		_error: { state: !0 },
		_tab: { state: !0 }
	};
	_unsubscribe;
	constructor() {
		super(), this.narrow = !1, this._tab = "Overview";
	}
	willUpdate(e) {
		e.has("hass") && this.hass && !this._unsubscribe && this._subscribe(this.hass);
	}
	disconnectedCallback() {
		super.disconnectedCallback();
		let e = this._unsubscribe;
		this._unsubscribe = void 0, e?.then((e) => e()).catch(() => void 0);
	}
	_subscribe(e) {
		this._unsubscribe = e.connection.subscribeMessage((e) => {
			this._rooms = e.rooms, this._error = void 0;
		}, { type: "poltergeist/subscribe" }), this._unsubscribe.catch((e) => {
			this._error = e.code ?? e.message ?? "unknown error";
		});
	}
	render() {
		return F`
      <header>
        ${this.narrow ? F`<button data-menu aria-label="Open sidebar" @click=${this._toggleMenu}>
              <svg viewBox="0 0 24 24" width="24" height="24"><path d=${De} /></svg>
            </button>` : L}
        <h1>Poltergeist</h1>
      </header>
      <nav role="tablist">
        ${Oe.map((e) => F`<button
            role="tab"
            aria-selected=${e === this._tab}
            @click=${() => this._tab = e}
          >
            ${e}
          </button>`)}
      </nav>
      <main>${this._renderTab()}</main>
    `;
	}
	_toggleMenu = () => this.dispatchEvent(new Event("hass-toggle-menu", {
		bubbles: !0,
		composed: !0
	}));
	_renderTab() {
		switch (this._tab) {
			case "Overview": return this._renderOverview();
			case "Sensors": return F`<poltergeist-sensors .hass=${this.hass}></poltergeist-sensors>`;
			default: return this._renderEmpty();
		}
	}
	_renderEmpty() {
		return F`<p class="note">Nothing here yet.</p>`;
	}
	_renderOverview() {
		return this._error ? F`<p class="note error">Could not load the rooms: ${this._error}</p>` : this._rooms ? this._rooms.length === 0 ? F`<p class="note">
        No rooms yet. Rooms are the areas of Home Assistant; create one and it appears here.
      </p>` : F`<div class="card">
      ${this._rooms.map((e) => e.probability === null ? F`<div class="row">
              <div class="name">${e.name}</div>
              <div class="none">no sensors</div>
            </div>` : F`<div class="row">
              <div class="name">${e.name}</div>
              <div class="bar" title=${e.sensors.join(", ")}>
                <div
                  class="fill"
                  style="width: ${Math.min(100, Math.max(0, e.probability))}%"
                ></div>
              </div>
              <div class="value">${he(e.probability)}</div>
              <div class="count">${ge(e.expected_count ?? 0)}</div>
            </div>`)}
    </div>` : F`<p class="note">Loading…</p>`;
	}
	static styles = o`
    :host {
      display: block;
      min-height: 100%;
      background: var(--primary-background-color);
      color: var(--primary-text-color);
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
    }
    header {
      display: flex;
      align-items: center;
      gap: 8px;
      height: var(--header-height, 56px);
      padding: 0 16px;
      background: var(--app-header-background-color, var(--primary-color));
      color: var(--app-header-text-color, var(--text-primary-color, #fff));
    }
    header h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 400;
    }
    header button {
      background: none;
      border: none;
      color: inherit;
      cursor: pointer;
      padding: 8px;
    }
    header svg {
      fill: currentColor;
    }
    nav {
      display: flex;
      overflow-x: auto;
      background: var(--app-header-background-color, var(--primary-color));
      color: var(--app-header-text-color, var(--text-primary-color, #fff));
    }
    nav button {
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      color: inherit;
      cursor: pointer;
      font: inherit;
      opacity: 0.75;
      padding: 12px 16px;
    }
    nav button[aria-selected="true"] {
      border-bottom-color: currentColor;
      opacity: 1;
    }
    main {
      max-width: 960px;
      margin: 0 auto;
      padding: 16px;
    }
    .card {
      background: var(--card-background-color);
      border-radius: var(--ha-card-border-radius, 12px);
      box-shadow: var(--ha-card-box-shadow, none);
      border: 1px solid var(--divider-color);
      overflow: hidden;
    }
    .row {
      display: grid;
      grid-template-columns: minmax(80px, 1fr) minmax(80px, 2fr) 56px 48px;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    .row:last-child {
      border-bottom: none;
    }
    .bar {
      height: 8px;
      border-radius: 4px;
      background: var(--divider-color);
      overflow: hidden;
    }
    .fill {
      height: 100%;
      background: var(--primary-color);
    }
    .value {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .count {
      text-align: right;
      color: var(--secondary-text-color);
      font-variant-numeric: tabular-nums;
    }
    .none {
      grid-column: 2 / -1;
      color: var(--secondary-text-color);
    }
    .note {
      color: var(--secondary-text-color);
    }
    .error {
      color: var(--error-color);
    }
  `;
};
customElements.define("poltergeist-panel", ke);
export { ke as PoltergeistPanel };
