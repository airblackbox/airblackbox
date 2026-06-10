{{- define "air-gateway.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "air-gateway.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "air-gateway.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "air-gateway.labels" -}}
app.kubernetes.io/name: {{ include "air-gateway.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "air-gateway.selectorLabels" -}}
app.kubernetes.io/name: {{ include "air-gateway.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
