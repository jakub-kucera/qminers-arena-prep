-- The audio edition's text: a pandoc filter run on each chapter's .qmd (scripts/audio.sh).
--   math        -> its speak="..." sentence (a span or an .eq div around it); math without one fails the build
--   tables      -> dropped; a ::: {.content-visible when-format="audio"} div next to one is read instead
--   code blocks -> "The command is in the printed edition."
--   inline code -> its text, underscores and dashes read as spaces
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

-- numbers as a voice should say them: +2,415 "plus", 1,477k "thousand"
local function Str(el)
  local text = el.text:gsub("^%+(%d)", "plus %1"):gsub("^[−%-](%d)", "minus %1"):gsub("(%d)k$", "%1 thousand"):gsub("(%d)k([%.,;:%)])", "%1 thousand%2")
  if text ~= el.text then
    return pandoc.Str(text)
  end
end

local function Math(el)
  table.insert(missing, el.text)
  return pandoc.Str(el.text)
end

local function Code(el)
  local text = el.text:gsub("%.md$", ""):gsub("^%-%-", ""):gsub("[_%-]", " "):gsub("|", " or ")
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
    Figure = Figure, Image = Image, Link = Link, Note = Note, Div = Div, Header = Header },
  { Pandoc = check },
}
