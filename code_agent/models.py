from django.db import models


class CodeProject(models.Model):
    user = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='code_projects'
    )
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True, default='')
    # Primary language hint (python, javascript, etc.)
    language = models.CharField(max_length=64, blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    @property
    def memory_project_id(self):
        """Offset to avoid collisions with novel project IDs in the shared MemoryNode table."""
        return 500000 + self.id


class CodeFile(models.Model):
    project = models.ForeignKey(CodeProject, on_delete=models.CASCADE, related_name='files')
    # Relative path within the project, e.g. "src/main.py"
    path = models.CharField(max_length=1024)
    content = models.TextField(blank=True, default='')
    language = models.CharField(max_length=64, blank=True, default='')
    # Current version number (increments on every accepted edit)
    current_version = models.IntegerField(default=1)
    # Link to corresponding MemoryNode for context retrieval
    memory_node_id = models.IntegerField(null=True, blank=True)
    size = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'path')
        ordering = ['path']

    def __str__(self):
        return f"{self.project.name}/{self.path}"

    def save(self, *args, **kwargs):
        self.size = len(self.content)
        super().save(*args, **kwargs)


class FileVersion(models.Model):
    """Version snapshot — created whenever an edit is confirmed."""
    file = models.ForeignKey(CodeFile, on_delete=models.CASCADE, related_name='versions')
    version = models.IntegerField()
    content = models.TextField()
    change_summary = models.CharField(max_length=512, blank=True, default='')
    # Serialised list of {original, replacement} diffs that were applied
    diffs_applied = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('file', 'version')
        ordering = ['file', 'version']

    def __str__(self):
        return f"{self.file.path} v{self.version}"


class CodeSession(models.Model):
    """One AI conversation thread scoped to a project (optionally a single file)."""
    project = models.ForeignKey(CodeProject, on_delete=models.CASCADE, related_name='sessions')
    # Optional: session is focused on a specific file
    focused_file = models.ForeignKey(
        CodeFile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sessions'
    )
    title = models.CharField(max_length=256, blank=True, default='新对话')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.project.name} — {self.title}"


class CodeMessage(models.Model):
    ROLES = [('user', '用户'), ('assistant', 'AI')]

    session = models.ForeignKey(CodeSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=16, choices=ROLES)
    content = models.TextField()
    # For assistant messages that contain code edit suggestions
    suggested_file_id = models.IntegerField(null=True, blank=True)
    # Diffs waiting for the user to accept/reject
    pending_diffs = models.JSONField(default=list)
    diffs_applied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"
