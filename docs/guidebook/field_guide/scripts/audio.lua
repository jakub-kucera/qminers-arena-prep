-- The audio edition's text: a pandoc filter run on each chapter's .qmd (scripts/audio.sh).
--   math        -> its speak="..." sentence (a span or an .eq div around it); math without one fails the build
--   tables      -> dropped; a ::: {.content-visible when-format="audio"} div next to one is read instead
--   code blocks -> "The command is in the printed edition."
--   inline code -> its text, underscores and dashes read as spaces; a path as its file's name, a module with spaces,
--                  the portal's figures as words
--   words       -> abbreviations (ch., pp., eq., et al.), signs, ranges and clock times as a voice says them
--   definitions -> each term followed by a full stop
--   figures     -> "Figure: " and the alt text
--   callouts    -> "Box: <title>." and the contents
--   @fig- refs  -> "the figure"

local missing = {}

local function spoken(text)
  return pandoc.Str(text)
end

local function says(attr)
  return attr and attr.attributes and attr.attributes.speak
end

local function Span(el)
  local speak = says(el.attr)
  if speak then
    return spoken(speak)
  end
  if el.classes:includes("src") then  -- a source citation: printed, not read
    return {}
  end
end

-- words a voice would mangle, as whole tokens (a token's brackets and trailing punctuation are kept around them)
local WORDS = {
  ["ch."] = "chapter", ["p."] = "page", ["pp."] = "pages", ["eq."] = "equation", ["al."] = "and others",
  ["×"] = "times", ["§"] = "section", ["e.g."] = "for example", ["i.e."] = "that is",
}

local function clock(h, m)
  h, m = tonumber(h), tonumber(m)
  local parts = {}
  if h > 0 then table.insert(parts, h .. (h == 1 and " hour" or " hours")) end
  if m > 0 then table.insert(parts, m .. " minutes") end
  return #parts > 0 and table.concat(parts, " ") or "the start"
end

-- numbers and abbreviations as a voice should say them: "plus 2,415", "1,477 thousand", "24 to 40", "T plus 30 minutes"
local function Str(el)
  local text = el.text
  local open, core, close = text:match("^([%(%[]*)(.-)([%)%]%.,;:]*)$")
  if WORDS[core] then
    text = open .. WORDS[core] .. close
  elseif WORDS[core .. close] then
    text = open .. WORDS[core .. close]
  end
  -- pandoc joins a known abbreviation to the next word with a no-break space ("pp. 317" is one token), so match prefixes
  local nbsp = "\194\160"
  for short, long in pairs({ ch = "chapter", pp = "pages", p = "page", eq = "equation" }) do
    text = text:gsub("^(%(?)" .. short .. "%." .. nbsp, "%1" .. long .. " "):gsub("^(%(?)" .. short .. "%.$", "%1" .. long)
  end
  text = text:gsub("§", "section "):gsub(nbsp, " ")
  if text == "et" then  -- "et al." (only ever that in this guide): the "al." token becomes "and others"
    return pandoc.Str("")
  end
  text = text:gsub("^al%.", "and others"):gsub("^(%(?)PnL", "%1P and L")
  -- Lua patterns work on bytes, so the minus sign (U+2212) and the en dash (U+2013) are matched as literal strings
  text = text:gsub("^(%(?)−", "%1minus "):gsub("^(%(?)%-([%d%$€])", "%1minus %2"):gsub("^(%(?)%+([%d%$€])", "%1plus %2")
  text = text:gsub("(%d)k$", "%1 thousand"):gsub("(%d)k([%.,;:%)])", "%1 thousand%2")
  text = text:gsub("(%d)–(%d)", "%1 to %2"):gsub("(%d)%%–(%d)", "%1%% to %2")
  text = text:gsub("^(%(?)T%+(%d):(%d%d)", function(o, h, m) return o .. "T plus " .. clock(h, m) end)
  text = text:gsub("^(%d):(%d%d)%.$", function(h, m) return clock(h, m) .. " in." end)
  if text ~= el.text then
    return pandoc.Str(text)
  end
end

local function Math(el)
  table.insert(missing, el.text)
  return pandoc.Str(el.text)
end

-- the portal's figures, as words
local FIGURES = {
  tradedVolume = "traded volume", markPrice = "mark price", breachPenalty = "breach penalty",
  pnlSe = "P and L standard error", absInventoryQ50 = "the absolute inventory's median",
  absInventoryQ68 = "its 68th percentile", absInventoryQ95 = "its 95th percentile",
  absInventoryQ997 = "its 99.7th percentile", pnl = "P and L", nbhd = "neighbourhood",
}

local function Code(el)
  local text = el.text
  if FIGURES[text] then
    return pandoc.Str(FIGURES[text])
  end
  if text:match("wiki/concepts/") then  -- a wiki page: its name
    return pandoc.Str("the wiki page " .. text:match("([^/]+)%.md$"):gsub("%-", " "))
  end
  if text:match("%.md$") then  -- a repo document: its name, in lower case so it isn't spelt out
    return pandoc.Str(text:match("([^/]+)%.md$"):gsub("[_%-]", " "):lower())
  end
  if text:match("/") then  -- any other path: its last part, without the extension
    text = text:match("([^/]+)/?$"):gsub("%.%w+$", "")
  elseif text:match("^[%a_]+%.[%a_.]+$") and not text:match("%.py$") then  -- a module: arena.grid
    text = text:gsub("%.", " ")
  end
  text = text:gsub("%.py$", ""):gsub("^%-%-", ""):gsub("[_%-<>]", " "):gsub("|", " or ")
  return pandoc.Str(text)
end

local function CodeBlock(_)
  return pandoc.Para({ pandoc.Str("The command is in the printed edition.") })
end

local function Table(_)
  return {}
end

local function Cite(el)
  local id = el.citations[1] and el.citations[1].id or ""
  if id:match("^fig%-") then
    return pandoc.Str("the figure")
  end
end

local function Figure(el)
  local alt = ""
  pandoc.walk_block(el, {
    Image = function(img)
      alt = img.attributes["fig-alt"] or pandoc.utils.stringify(img.caption)
    end,
  })
  if alt == "" then
    alt = pandoc.utils.stringify(el.caption)
  end
  return pandoc.Para({ pandoc.Str("Figure: " .. alt) })
end

local function Image(el)
  return pandoc.Str("Figure: " .. (el.attributes["fig-alt"] or pandoc.utils.stringify(el.caption)))
end

local function Link(el)
  return el.content
end

local function Note(_)
  return {}
end

local function Div(el)
  local speak = says(el.attr)
  if el.classes:includes("eq") and speak then
    return pandoc.Para({ spoken(speak) })
  end
  local when = el.attributes["when-format"]
  if el.classes:includes("content-visible") then
    if when == "audio" then
      return el.content
    end
    return {}
  end
  if el.classes:includes("content-hidden") and when == "audio" then
    return {}
  end
  for _, class in ipairs(el.classes) do
    if class:match("^callout") then
      local title = el.attributes.title or "Note"
      if title == "In the repo" then  -- files and commands: nothing a listener can use
        return pandoc.Para({ pandoc.Str("Box: In the repo. The files and commands are in the printed edition.") })
      end
      local blocks = { pandoc.Para({ pandoc.Str("Box: " .. title .. ".") }) }
      for _, block in ipairs(el.content) do
        table.insert(blocks, block)
      end
      table.insert(blocks, pandoc.Para({ pandoc.Str("End of box.") }))
      return blocks
    end
  end
end

local function Header(el)
  -- a pause after each heading, so the voice doesn't run it into the next sentence
  local text = pandoc.utils.stringify(el.content)
  return pandoc.Para({ pandoc.Str(text:match("[%.%?!:]$") and text or text .. ".") })
end

local function DefinitionList(el)
  local blocks = {}
  for _, item in ipairs(el.content) do
    local term = pandoc.utils.stringify(item[1]):gsub("_", " ")
    local first = true
    for _, definition in ipairs(item[2]) do
      for _, block in ipairs(definition) do
        if first and block.t == "Para" or first and block.t == "Plain" then
          local inlines = { pandoc.Str(term .. "."), pandoc.Space() }
          for _, inline in ipairs(block.content) do table.insert(inlines, inline) end
          table.insert(blocks, pandoc.Para(inlines))
          first = false
        else
          table.insert(blocks, block)
        end
      end
    end
  end
  return blocks
end

local function check(doc)
  if #missing > 0 then
    io.stderr:write("audio.lua: formulas without a speak sentence:\n")
    for _, text in ipairs(missing) do
      io.stderr:write("  $" .. text .. "$\n")
    end
    os.exit(1)
  end
  return doc
end

-- top-down, so a span or div with speak="..." replaces its math before the math itself is visited
return {
  { traverse = "topdown", Span = Span, Str = Str, Math = Math, Code = Code, CodeBlock = CodeBlock, Table = Table, Cite = Cite,
    Figure = Figure, Image = Image, Link = Link, Note = Note, Div = Div, Header = Header,
    DefinitionList = DefinitionList },
  { Pandoc = check },
}
