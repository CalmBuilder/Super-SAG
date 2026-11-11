use anyhow::{bail, Context, Result};
use sag_protocol::types::{FolderIndexOptions, Settings};
use std::{collections::HashMap, fs, io::{ErrorKind, Write}, path::{Path, PathBuf}};

const START: &str = "# Super-SAG index options: begin";
const END: &str = "# Super-SAG index options: end";
const LEGACY_START: &str = "# SAG Wiki index options: begin";
const LEGACY_END: &str = "# SAG Wiki index options: end";

struct ManagedBlock {
    range: std::ops::Range<usize>,
    legacy: bool,
}

pub struct Rules {
    root: PathBuf,
    directories: HashMap<PathBuf, FolderIndexOptions>,
}

impl Rules {
    pub fn new(root: &Path, settings: &Settings) -> Result<Self> {
        let options = read(root)?.unwrap_or_else(|| FolderIndexOptions {
            extensions: None,
            file_types: settings.file_types.clone(), convert_other_formats: settings.convert_other_formats,
            conversion_formats: settings.conversion_formats.clone(),
        });
        Ok(Self { root: root.into(), directories: HashMap::from([(root.into(), options)]) })
    }
    pub fn directory(&mut self, directory: &Path) -> Result<&FolderIndexOptions> {
        let relative = directory.strip_prefix(&self.root).context("规则查询超出知识库目录")?;
        if relative.components().any(|part| matches!(part, std::path::Component::ParentDir)) {
            bail!("规则查询超出知识库目录")
        }
        if !self.directories.contains_key(directory) {
            let options = match read(directory)? {
                Some(options) => options,
                None => self.directory(directory.parent().context("规则目录没有父目录")?)?.clone(),
            };
            self.directories.insert(directory.into(), options);
        }
        Ok(&self.directories[directory])
    }
    pub fn file(&mut self, path: &Path) -> Result<&FolderIndexOptions> {
        // Native notifications may describe the registered directory itself.
        if path == self.root { return Ok(&self.directories[&self.root]); }
        let directory = match path.strip_prefix(self.root.join(crate::docling::OUTPUT_DIRECTORY)) {
            Ok(relative) => self.root.join(relative.parent().context("转换路径没有父目录")?),
            Err(_) => path.parent().context("索引路径没有父目录")?.into(),
        };
        self.directory(&directory)
    }
    pub fn converts_files(&self) -> bool {
        self.directories.values().any(|options| options.file_types.text || options.convert_other_formats || options.extensions.as_ref().is_some_and(|extensions| extensions.iter().any(|extension| crate::anydoc::handles(Path::new(&format!("file.{extension}"))))))
    }
}

fn content(root: &Path) -> Result<String> {
    match fs::read_to_string(root.join(".sagignore")) {
        Ok(content) => Ok(content),
        Err(error) if error.kind() == ErrorKind::NotFound => Ok(String::new()),
        // A directory we cannot enter has nothing to index, so its missing
        // options are harmless; the walk records the directory as an issue.
        // A readable directory whose rules file is unreadable must fail
        // closed: guessing "no rules" could index files the user excluded.
        Err(error) if error.kind() == ErrorKind::PermissionDenied && fs::read_dir(root).is_err() => Ok(String::new()),
        Err(error) => Err(error).context("无法读取 .sagignore"),
    }
}

fn block(content: &str) -> Result<Option<ManagedBlock>> {
    let mut result = None;
    let mut open = None;
    let mut offset = 0;
    for part in content.split_inclusive('\n') {
        let line = part.trim_end_matches(['\r', '\n']);
        let line = if offset == 0 { line.strip_prefix('\u{feff}').unwrap_or(line) } else { line };
        let marker = line.trim();
        let start = match marker { START => Some(false), LEGACY_START => Some(true), _ => None };
        let end = match marker { END => Some(false), LEGACY_END => Some(true), _ => None };
        if let Some(legacy) = start {
            if open.is_some() || result.is_some() {
                bail!(".sagignore 中存在重复或嵌套的索引选项标记，请先修复该文件");
            }
            let prefix = part.find(marker).expect("marker belongs to this line");
            open = Some((offset + prefix, legacy));
        }
        if let Some(legacy) = end {
            let Some((start, start_legacy)) = open.take() else {
                bail!(".sagignore 中的索引选项标记不完整，请先修复该文件");
            };
            if start_legacy != legacy || result.is_some() {
                bail!(".sagignore 中的索引选项标记不匹配，请先修复该文件");
            }
            let prefix = part.find(marker).expect("marker belongs to this line");
            result = Some(ManagedBlock { range: start..offset + prefix + marker.len(), legacy });
        }
        offset += part.len();
    }
    if open.is_some() { bail!(".sagignore 中的索引选项标记不完整，请先修复该文件"); }
    Ok(result)
}

fn parse_options(content: &str, block: &ManagedBlock) -> Result<FolderIndexOptions> {
    let lines: Vec<_> = content[block.range.clone()].lines().collect();
    if lines.len() != 3 { bail!(".sagignore 中的索引选项块包含意外内容，请先修复该文件"); }
    let json = lines[1].strip_prefix("# ").context(".sagignore 中的索引选项格式不正确")?;
    serde_json::from_str(json).context("无法解析 .sagignore 中的索引选项")
}

pub fn read(root: &Path) -> Result<Option<FolderIndexOptions>> {
    let content = content(root)?;
    let Some(block) = block(&content)? else { return Ok(None); };
    Ok(Some(parse_options(&content, &block)?))
}

pub fn write(root: &Path, options: &FolderIndexOptions) -> Result<()> {
    let path = root.join(".sagignore");
    let mut content = content(root)?;
    let existing = block(&content)?;
    if let Some(block) = &existing { parse_options(&content, block)?; }
    let newline = if content.contains("\r\n") { "\r\n" } else { "\n" };
    let (start, end) = if existing.as_ref().is_some_and(|block| block.legacy) { (LEGACY_START, LEGACY_END) } else { (START, END) };
    let replacement = format!("{start}{newline}# {}{newline}{end}", serde_json::to_string(options)?);
    if let Some(block) = existing { content.replace_range(block.range, &replacement); }
    else {
        if !content.is_empty() && !content.ends_with('\n') { content.push_str(newline); }
        content.push_str(&replacement);
        content.push_str(newline);
    }
    let mut file = tempfile::NamedTempFile::new_in(root)?;
    if path.exists() { file.as_file().set_permissions(fs::metadata(&path)?.permissions())?; }
    file.write_all(content.as_bytes())?;
    file.persist(path).map_err(|error| error.error).context("无法保存 .sagignore")?;
    Ok(())
}
