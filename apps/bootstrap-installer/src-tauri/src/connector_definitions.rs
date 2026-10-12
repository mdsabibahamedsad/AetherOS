use crate::connector_manager::*;

pub fn all_definitions() -> Vec<ConnectorDefinition> {
    vec![
        telegram(),
        discord(),
        slack(),
        gmail(),
        outlook(),
        microsoft_teams(),
        whatsapp(),
        github(),
        gitlab(),
        notion(),
        google_drive(),
        one_drive(),
        dropbox(),
        google_calendar(),
        outlook_calendar(),
        jira(),
        linear(),
        trello(),
        clickup(),
        zoom(),
        google_meet(),
        rss(),
        webhook(),
        custom_http(),
    ]
}

pub fn get_definition(id: &str) -> Option<ConnectorDefinition> {
    all_definitions().into_iter().find(|d| d.id == id)
}

fn telegram() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "telegram".into(),
        name: "Telegram".into(),
        description: "Connect Telegram bot for messaging, notifications, and automation".into(),
        category: ConnectorCategory::Messaging,
        auth_type: AuthType::Token {
            label: "Bot Token".into(),
            placeholder: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11".into(),
        },
        capabilities: vec![
            ConnectorCapability::SendMessage, ConnectorCapability::ReceiveMessage,
            ConnectorCapability::WebhookReceive,
        ],
        config_schema: vec![
            ConfigField { key: "bot_username".into(), label: "Bot Username".into(), field_type: ConfigFieldType::Text, required: true, placeholder: "my_bot".into(), default_value: None, secret: false },
            ConfigField { key: "webhook_url".into(), label: "Webhook URL".into(), field_type: ConfigFieldType::Url, required: false, placeholder: "https://example.com/webhook".into(), default_value: None, secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "5".into(), default_value: Some("5".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/telegram.svg".into(),
        website: "https://telegram.org".into(),
        version: "1.0.0".into(),
    }
}

fn discord() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "discord".into(),
        name: "Discord".into(),
        description: "Connect Discord bot for server management, messaging, and moderation".into(),
        category: ConnectorCategory::Messaging,
        auth_type: AuthType::Token {
            label: "Bot Token".into(),
            placeholder: "MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.Gabcde.12345".into(),
        },
        capabilities: vec![
            ConnectorCapability::SendMessage, ConnectorCapability::ReceiveMessage,
            ConnectorCapability::ReadNotifications,
        ],
        config_schema: vec![
            ConfigField { key: "guild_id".into(), label: "Server/Guild ID".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "123456789012345678".into(), default_value: None, secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "5".into(), default_value: Some("5".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/discord.svg".into(),
        website: "https://discord.com".into(),
        version: "1.0.0".into(),
    }
}

fn slack() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "slack".into(),
        name: "Slack".into(),
        description: "Connect Slack workspace for messaging, channels, and notifications".into(),
        category: ConnectorCategory::Messaging,
        auth_type: AuthType::Token {
            label: "Bot Token".into(),
            placeholder: "xoxb-123456789012-1234567890123-abc123def456".into(),
        },
        capabilities: vec![
            ConnectorCapability::SendMessage, ConnectorCapability::ReceiveMessage,
            ConnectorCapability::SendNotifications,
        ],
        config_schema: vec![
            ConfigField { key: "default_channel".into(), label: "Default Channel".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "#general".into(), default_value: None, secret: false },
            ConfigField { key: "signing_secret".into(), label: "Signing Secret".into(), field_type: ConfigFieldType::Password, required: false, placeholder: "abc123def456...".into(), default_value: None, secret: true },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/slack.svg".into(),
        website: "https://slack.com".into(),
        version: "1.0.0".into(),
    }
}

fn gmail() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "gmail".into(),
        name: "Gmail".into(),
        description: "Connect Gmail for email reading, sending, and automation".into(),
        category: ConnectorCategory::Email,
        auth_type: AuthType::OAuth2 {
            client_id: "aetheros-gmail-client".into(),
            scopes: vec!["https://www.googleapis.com/auth/gmail.modify".into()],
            auth_url: "https://accounts.google.com/o/oauth2/auth".into(),
            token_url: "https://oauth2.googleapis.com/token".into(),
            redirect_uri: "aetheros://oauth/gmail".into(),
        },
        capabilities: vec![
            ConnectorCapability::ReadMail, ConnectorCapability::SendMail,
            ConnectorCapability::ReadNotifications,
        ],
        config_schema: vec![
            ConfigField { key: "email_address".into(), label: "Email Address".into(), field_type: ConfigFieldType::Email, required: true, placeholder: "user@gmail.com".into(), default_value: None, secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "30".into(), default_value: Some("30".into()), secret: false },
            ConfigField { key: "max_results".into(), label: "Max Results per Poll".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "50".into(), default_value: Some("50".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/gmail.svg".into(),
        website: "https://mail.google.com".into(),
        version: "1.0.0".into(),
    }
}

fn outlook() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "outlook".into(),
        name: "Outlook".into(),
        description: "Connect Outlook/Hotmail for email management and automation".into(),
        category: ConnectorCategory::Email,
        auth_type: AuthType::OAuth2 {
            client_id: "aetheros-outlook-client".into(),
            scopes: vec!["Mail.ReadWrite".into(), "Mail.Send".into(), "User.Read".into()],
            auth_url: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize".into(),
            token_url: "https://login.microsoftonline.com/common/oauth2/v2.0/token".into(),
            redirect_uri: "aetheros://oauth/outlook".into(),
        },
        capabilities: vec![
            ConnectorCapability::ReadMail, ConnectorCapability::SendMail,
        ],
        config_schema: vec![
            ConfigField { key: "email_address".into(), label: "Email Address".into(), field_type: ConfigFieldType::Email, required: true, placeholder: "user@outlook.com".into(), default_value: None, secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "30".into(), default_value: Some("30".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/outlook.svg".into(),
        website: "https://outlook.com".into(),
        version: "1.0.0".into(),
    }
}

fn microsoft_teams() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "microsoft_teams".into(),
        name: "Microsoft Teams".into(),
        description: "Connect Microsoft Teams for messaging, channels, and meetings".into(),
        category: ConnectorCategory::Messaging,
        auth_type: AuthType::OAuth2 {
            client_id: "aetheros-teams-client".into(),
            scopes: vec!["ChannelMessage.Read.All".into(), "ChannelMessage.Send".into(), "Chat.ReadWrite".into()],
            auth_url: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize".into(),
            token_url: "https://login.microsoftonline.com/common/oauth2/v2.0/token".into(),
            redirect_uri: "aetheros://oauth/teams".into(),
        },
        capabilities: vec![
            ConnectorCapability::SendMessage, ConnectorCapability::ReceiveMessage,
            ConnectorCapability::SendNotifications,
        ],
        config_schema: vec![
            ConfigField { key: "tenant_id".into(), label: "Tenant ID".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "common".into(), default_value: Some("common".into()), secret: false },
            ConfigField { key: "team_id".into(), label: "Team ID".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "".into(), default_value: None, secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/teams.svg".into(),
        website: "https://teams.microsoft.com".into(),
        version: "1.0.0".into(),
    }
}

fn whatsapp() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "whatsapp".into(),
        name: "WhatsApp Business".into(),
        description: "Connect WhatsApp Business API for messaging and notifications".into(),
        category: ConnectorCategory::Messaging,
        auth_type: AuthType::Token {
            label: "Access Token".into(),
            placeholder: "EAAx...".into(),
        },
        capabilities: vec![
            ConnectorCapability::SendMessage, ConnectorCapability::ReceiveMessage,
        ],
        config_schema: vec![
            ConfigField { key: "phone_number_id".into(), label: "Phone Number ID".into(), field_type: ConfigFieldType::Text, required: true, placeholder: "123456789012345".into(), default_value: None, secret: false },
            ConfigField { key: "business_account_id".into(), label: "Business Account ID".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "".into(), default_value: None, secret: false },
            ConfigField { key: "webhook_url".into(), label: "Webhook URL".into(), field_type: ConfigFieldType::Url, required: false, placeholder: "https://example.com/webhook".into(), default_value: None, secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/whatsapp.svg".into(),
        website: "https://business.whatsapp.com".into(),
        version: "1.0.0".into(),
    }
}

fn github() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "github".into(),
        name: "GitHub".into(),
        description: "Connect GitHub for repositories, issues, PRs, and actions".into(),
        category: ConnectorCategory::SourceControl,
        auth_type: AuthType::Token {
            label: "Personal Access Token".into(),
            placeholder: "ghp_xxxxxxxxxxxxxxxxxxxx".into(),
        },
        capabilities: vec![
            ConnectorCapability::ListIssues, ConnectorCapability::CreateIssue,
            ConnectorCapability::UpdateIssue, ConnectorCapability::ListRepos,
            ConnectorCapability::WebhookReceive,
        ],
        config_schema: vec![
            ConfigField { key: "owner".into(), label: "Repository Owner".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "username or org".into(), default_value: None, secret: false },
            ConfigField { key: "repo".into(), label: "Repository Name".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "my-repo".into(), default_value: None, secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "60".into(), default_value: Some("60".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/github.svg".into(),
        website: "https://github.com".into(),
        version: "1.0.0".into(),
    }
}

fn gitlab() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "gitlab".into(),
        name: "GitLab".into(),
        description: "Connect GitLab for repositories, merge requests, and CI/CD".into(),
        category: ConnectorCategory::SourceControl,
        auth_type: AuthType::Token {
            label: "Personal Access Token".into(),
            placeholder: "glpat-xxxxxxxxxxxx".into(),
        },
        capabilities: vec![
            ConnectorCapability::ListIssues, ConnectorCapability::CreateIssue,
            ConnectorCapability::UpdateIssue, ConnectorCapability::ListRepos,
            ConnectorCapability::WebhookReceive,
        ],
        config_schema: vec![
            ConfigField { key: "base_url".into(), label: "GitLab URL".into(), field_type: ConfigFieldType::Url, required: false, placeholder: "https://gitlab.com".into(), default_value: Some("https://gitlab.com".into()), secret: false },
            ConfigField { key: "project_id".into(), label: "Project ID".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "12345".into(), default_value: None, secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "60".into(), default_value: Some("60".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/gitlab.svg".into(),
        website: "https://gitlab.com".into(),
        version: "1.0.0".into(),
    }
}

fn notion() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "notion".into(),
        name: "Notion".into(),
        description: "Connect Notion for pages, databases, and workspace management".into(),
        category: ConnectorCategory::Storage,
        auth_type: AuthType::Token {
            label: "Integration Token".into(),
            placeholder: "secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx".into(),
        },
        capabilities: vec![
            ConnectorCapability::SearchContent, ConnectorCapability::CreateDocument,
            ConnectorCapability::ReadDatabase,
        ],
        config_schema: vec![
            ConfigField { key: "database_id".into(), label: "Database ID".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "".into(), default_value: None, secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/notion.svg".into(),
        website: "https://notion.so".into(),
        version: "1.0.0".into(),
    }
}

fn google_drive() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "google_drive".into(),
        name: "Google Drive".into(),
        description: "Connect Google Drive for file storage, sharing, and management".into(),
        category: ConnectorCategory::Storage,
        auth_type: AuthType::OAuth2 {
            client_id: "aetheros-drive-client".into(),
            scopes: vec!["https://www.googleapis.com/auth/drive.readonly".into()],
            auth_url: "https://accounts.google.com/o/oauth2/auth".into(),
            token_url: "https://oauth2.googleapis.com/token".into(),
            redirect_uri: "aetheros://oauth/drive".into(),
        },
        capabilities: vec![
            ConnectorCapability::ListFiles, ConnectorCapability::DownloadFile,
            ConnectorCapability::UploadFile, ConnectorCapability::SearchContent,
        ],
        config_schema: vec![
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "300".into(), default_value: Some("300".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/googledrive.svg".into(),
        website: "https://drive.google.com".into(),
        version: "1.0.0".into(),
    }
}

fn one_drive() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "one_drive".into(),
        name: "OneDrive".into(),
        description: "Connect Microsoft OneDrive for file storage and sharing".into(),
        category: ConnectorCategory::Storage,
        auth_type: AuthType::OAuth2 {
            client_id: "aetheros-onedrive-client".into(),
            scopes: vec!["Files.ReadWrite.All".into(), "offline_access".into()],
            auth_url: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize".into(),
            token_url: "https://login.microsoftonline.com/common/oauth2/v2.0/token".into(),
            redirect_uri: "aetheros://oauth/onedrive".into(),
        },
        capabilities: vec![
            ConnectorCapability::ListFiles, ConnectorCapability::DownloadFile,
            ConnectorCapability::UploadFile,
        ],
        config_schema: vec![
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "300".into(), default_value: Some("300".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/onedrive.svg".into(),
        website: "https://onedrive.live.com".into(),
        version: "1.0.0".into(),
    }
}

fn dropbox() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "dropbox".into(),
        name: "Dropbox".into(),
        description: "Connect Dropbox for file storage, sync, and sharing".into(),
        category: ConnectorCategory::Storage,
        auth_type: AuthType::OAuth2 {
            client_id: "aetheros-dropbox-client".into(),
            scopes: vec!["files.metadata.read".into(), "files.content.read".into(), "files.content.write".into()],
            auth_url: "https://www.dropbox.com/oauth2/authorize".into(),
            token_url: "https://api.dropboxapi.com/oauth2/token".into(),
            redirect_uri: "aetheros://oauth/dropbox".into(),
        },
        capabilities: vec![
            ConnectorCapability::ListFiles, ConnectorCapability::UploadFile,
            ConnectorCapability::DownloadFile,
        ],
        config_schema: vec![
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "300".into(), default_value: Some("300".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/dropbox.svg".into(),
        website: "https://dropbox.com".into(),
        version: "1.0.0".into(),
    }
}

fn google_calendar() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "google_calendar".into(),
        name: "Google Calendar".into(),
        description: "Connect Google Calendar for events, scheduling, and reminders".into(),
        category: ConnectorCategory::Calendar,
        auth_type: AuthType::OAuth2 {
            client_id: "aetheros-calendar-client".into(),
            scopes: vec!["https://www.googleapis.com/auth/calendar.readonly".into()],
            auth_url: "https://accounts.google.com/o/oauth2/auth".into(),
            token_url: "https://oauth2.googleapis.com/token".into(),
            redirect_uri: "aetheros://oauth/calendar".into(),
        },
        capabilities: vec![
            ConnectorCapability::ListEvents, ConnectorCapability::CreateEvent,
        ],
        config_schema: vec![
            ConfigField { key: "calendar_id".into(), label: "Calendar ID".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "primary".into(), default_value: Some("primary".into()), secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "300".into(), default_value: Some("300".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/googlecalendar.svg".into(),
        website: "https://calendar.google.com".into(),
        version: "1.0.0".into(),
    }
}

fn outlook_calendar() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "outlook_calendar".into(),
        name: "Outlook Calendar".into(),
        description: "Connect Outlook Calendar for events and scheduling".into(),
        category: ConnectorCategory::Calendar,
        auth_type: AuthType::OAuth2 {
            client_id: "aetheros-outlook-cal-client".into(),
            scopes: vec!["Calendars.ReadWrite".into(), "offline_access".into()],
            auth_url: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize".into(),
            token_url: "https://login.microsoftonline.com/common/oauth2/v2.0/token".into(),
            redirect_uri: "aetheros://oauth/outlook-cal".into(),
        },
        capabilities: vec![
            ConnectorCapability::ListEvents, ConnectorCapability::CreateEvent,
        ],
        config_schema: vec![
            ConfigField { key: "calendar_id".into(), label: "Calendar ID".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "".into(), default_value: None, secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "300".into(), default_value: Some("300".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/outlookcalendar.svg".into(),
        website: "https://outlook.live.com/calendar".into(),
        version: "1.0.0".into(),
    }
}

fn jira() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "jira".into(),
        name: "Jira".into(),
        description: "Connect Jira for issue tracking, sprints, and project management".into(),
        category: ConnectorCategory::ProjectManagement,
        auth_type: AuthType::Basic {
            username_label: "Email".into(),
            password_label: "API Token".into(),
        },
        capabilities: vec![
            ConnectorCapability::ListIssues, ConnectorCapability::CreateIssue,
            ConnectorCapability::UpdateIssue, ConnectorCapability::ManageWorkflow,
        ],
        config_schema: vec![
            ConfigField { key: "base_url".into(), label: "Jira Instance URL".into(), field_type: ConfigFieldType::Url, required: true, placeholder: "https://your-domain.atlassian.net".into(), default_value: None, secret: false },
            ConfigField { key: "project_key".into(), label: "Project Key".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "PROJ".into(), default_value: None, secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "120".into(), default_value: Some("120".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/jira.svg".into(),
        website: "https://www.atlassian.com/software/jira".into(),
        version: "1.0.0".into(),
    }
}

fn linear() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "linear".into(),
        name: "Linear".into(),
        description: "Connect Linear for issue tracking and product management".into(),
        category: ConnectorCategory::ProjectManagement,
        auth_type: AuthType::ApiKey {
            label: "API Key".into(),
            placeholder: "lin_api_xxxxxxxxxxxx".into(),
        },
        capabilities: vec![
            ConnectorCapability::ListIssues, ConnectorCapability::CreateIssue,
            ConnectorCapability::UpdateIssue,
        ],
        config_schema: vec![
            ConfigField { key: "team_id".into(), label: "Team ID".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "".into(), default_value: None, secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "60".into(), default_value: Some("60".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/linear.svg".into(),
        website: "https://linear.app".into(),
        version: "1.0.0".into(),
    }
}

fn trello() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "trello".into(),
        name: "Trello".into(),
        description: "Connect Trello for board and card management".into(),
        category: ConnectorCategory::ProjectManagement,
        auth_type: AuthType::Token {
            label: "API Token".into(),
            placeholder: "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx".into(),
        },
        capabilities: vec![
            ConnectorCapability::CreateIssue, ConnectorCapability::ManageWorkflow,
        ],
        config_schema: vec![
            ConfigField { key: "api_key".into(), label: "API Key".into(), field_type: ConfigFieldType::Password, required: true, placeholder: "".into(), default_value: None, secret: true },
            ConfigField { key: "board_id".into(), label: "Board ID".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "".into(), default_value: None, secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "120".into(), default_value: Some("120".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/trello.svg".into(),
        website: "https://trello.com".into(),
        version: "1.0.0".into(),
    }
}

fn clickup() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "clickup".into(),
        name: "ClickUp".into(),
        description: "Connect ClickUp for task and project management".into(),
        category: ConnectorCategory::ProjectManagement,
        auth_type: AuthType::Token {
            label: "API Token".into(),
            placeholder: "pk_xxxxxxxx_xxxxxxxxxxxx".into(),
        },
        capabilities: vec![
            ConnectorCapability::ListIssues, ConnectorCapability::CreateIssue,
            ConnectorCapability::ManageWorkflow,
        ],
        config_schema: vec![
            ConfigField { key: "team_id".into(), label: "Team ID".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "".into(), default_value: None, secret: false },
            ConfigField { key: "space_id".into(), label: "Space ID".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "".into(), default_value: None, secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "120".into(), default_value: Some("120".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/clickup.svg".into(),
        website: "https://clickup.com".into(),
        version: "1.0.0".into(),
    }
}

fn zoom() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "zoom".into(),
        name: "Zoom".into(),
        description: "Connect Zoom for meeting management, scheduling, and notifications".into(),
        category: ConnectorCategory::VideoConferencing,
        auth_type: AuthType::OAuth2 {
            client_id: "aetheros-zoom-client".into(),
            scopes: vec!["meeting:read".into(), "meeting:write".into(), "user:read".into()],
            auth_url: "https://zoom.us/oauth/authorize".into(),
            token_url: "https://zoom.us/oauth/token".into(),
            redirect_uri: "aetheros://oauth/zoom".into(),
        },
        capabilities: vec![
            ConnectorCapability::ReceiveCalls, ConnectorCapability::InitiateCalls,
        ],
        config_schema: vec![
            ConfigField { key: "account_id".into(), label: "Account ID".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "".into(), default_value: None, secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/zoom.svg".into(),
        website: "https://zoom.us".into(),
        version: "1.0.0".into(),
    }
}

fn google_meet() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "google_meet".into(),
        name: "Google Meet".into(),
        description: "Connect Google Meet for video conferencing and scheduling".into(),
        category: ConnectorCategory::VideoConferencing,
        auth_type: AuthType::OAuth2 {
            client_id: "aetheros-meet-client".into(),
            scopes: vec!["https://www.googleapis.com/auth/calendar.readonly".into()],
            auth_url: "https://accounts.google.com/o/oauth2/auth".into(),
            token_url: "https://oauth2.googleapis.com/token".into(),
            redirect_uri: "aetheros://oauth/meet".into(),
        },
        capabilities: vec![
            ConnectorCapability::ReceiveCalls, ConnectorCapability::InitiateCalls,
        ],
        config_schema: vec![],
        icon_url: "https://cdn.aetheros.com/connectors/googlemeet.svg".into(),
        website: "https://meet.google.com".into(),
        version: "1.0.0".into(),
    }
}

fn rss() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "rss".into(),
        name: "RSS".into(),
        description: "Subscribe to RSS/Atom feeds for content updates and monitoring".into(),
        category: ConnectorCategory::Rss,
        auth_type: AuthType::None,
        capabilities: vec![ConnectorCapability::ReceiveMessage],
        config_schema: vec![
            ConfigField { key: "feed_url".into(), label: "Feed URL".into(), field_type: ConfigFieldType::Url, required: true, placeholder: "https://example.com/feed.xml".into(), default_value: None, secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "600".into(), default_value: Some("600".into()), secret: false },
            ConfigField { key: "max_items".into(), label: "Max Items".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "50".into(), default_value: Some("50".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/rss.svg".into(),
        website: "https://en.wikipedia.org/wiki/RSS".into(),
        version: "1.0.0".into(),
    }
}

fn webhook() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "webhook".into(),
        name: "Webhook".into(),
        description: "Receive and send webhooks for custom integrations and automation".into(),
        category: ConnectorCategory::Webhook,
        auth_type: AuthType::Token {
            label: "Secret Token".into(),
            placeholder: "whsec_xxxxxxxx".into(),
        },
        capabilities: vec![
            ConnectorCapability::WebhookReceive, ConnectorCapability::WebhookSend,
        ],
        config_schema: vec![
            ConfigField { key: "endpoint_path".into(), label: "Endpoint Path".into(), field_type: ConfigFieldType::Text, required: true, placeholder: "/webhook/my-service".into(), default_value: None, secret: false },
            ConfigField { key: "allowed_methods".into(), label: "Allowed Methods".into(), field_type: ConfigFieldType::Select { options: vec!["POST".into(), "GET".into(), "PUT".into(), "PATCH".into(), "DELETE".into()] }, required: false, placeholder: "POST".into(), default_value: Some("POST".into()), secret: false },
            ConfigField { key: "require_auth".into(), label: "Require Authentication".into(), field_type: ConfigFieldType::Boolean, required: false, placeholder: "true".into(), default_value: Some("true".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/webhook.svg".into(),
        website: "https://en.wikipedia.org/wiki/Webhook".into(),
        version: "1.0.0".into(),
    }
}

fn custom_http() -> ConnectorDefinition {
    ConnectorDefinition {
        id: "custom_http".into(),
        name: "Custom HTTP API".into(),
        description: "Connect any HTTP API for custom integrations and data exchange".into(),
        category: ConnectorCategory::CustomHttp,
        auth_type: AuthType::ApiKey {
            label: "API Key".into(),
            placeholder: "your-api-key".into(),
        },
        capabilities: vec![
            ConnectorCapability::SendMessage, ConnectorCapability::ReceiveMessage,
            ConnectorCapability::SearchContent,
        ],
        config_schema: vec![
            ConfigField { key: "base_url".into(), label: "Base URL".into(), field_type: ConfigFieldType::Url, required: true, placeholder: "https://api.example.com/v1".into(), default_value: None, secret: false },
            ConfigField { key: "auth_header".into(), label: "Auth Header Name".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "Authorization".into(), default_value: Some("Authorization".into()), secret: false },
            ConfigField { key: "auth_prefix".into(), label: "Auth Prefix".into(), field_type: ConfigFieldType::Text, required: false, placeholder: "Bearer ".into(), default_value: Some("Bearer ".into()), secret: false },
            ConfigField { key: "poll_interval".into(), label: "Poll Interval (seconds)".into(), field_type: ConfigFieldType::Number, required: false, placeholder: "60".into(), default_value: Some("60".into()), secret: false },
        ],
        icon_url: "https://cdn.aetheros.com/connectors/customhttp.svg".into(),
        website: "".into(),
        version: "1.0.0".into(),
    }
}

#[tauri::command]
pub async fn hub_get_connector_definitions() -> Result<Vec<ConnectorDefinition>, String> {
    Ok(all_definitions())
}

#[tauri::command]
pub async fn hub_get_connector_definition(definition_id: String) -> Result<Option<ConnectorDefinition>, String> {
    Ok(get_definition(&definition_id))
}
