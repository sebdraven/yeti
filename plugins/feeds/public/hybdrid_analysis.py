import logging
from datetime import timedelta

from core.errors import ObservableValidationError
from core.feed import Feed
from core.observables import Hash, Hostname, File


class Hybrid_Analysis(Feed):

    default_values = {
        "frequency":
            timedelta(minutes=5),
        "name":
            "Hybdrid-Analysis",
        "source":
            "https://www.hybrid-analysis.com/feed?json",
        "description":
            "Hybrid Analysis Public Feeds",
    }

    def update(self):
        for item in self.update_json(headers={'User-agent': 'VxApi Connector'})['data']:
            self.analyze(item)

    def analyze(self, item):
        f_hyb = File.get_or_create(value='FILE: {}'.format(item['sha256']))

        sha256 = Hash.get_or_create(value=item['sha256'])
        tags = []
        context = {'source': self.name}

        if 'vxfamily' in item:
            tags.append(' '.join(item['vxfamily'].split('.')))

        if 'tags' in item:
            tags.extend(item['tags'])

        if 'threatlevel_human' in item:
            context['threatlevel_human'] = item['threatlevel_human']

        if 'threatlevel' in item:
            context['threatlevel'] = item['threatlevel']

        if 'type' in item:
            context['type'] = item['type']

        if 'size' in item:
            context['size'] = item['size']

        if 'vt_detect' in item:
            context['virustotal_score'] = item['vt_detect']

        if 'et_alerts_total' in item:
            context['et_alerts_total'] = item['et_alerts_total']

        if 'process_list' in item:
            context['count_process_spawn'] = len(item['process_list'])

        context['url'] = 'https://www.hybrid-analysis.com' + item['reporturl']

        f_hyb.add_context(context)
        f_hyb.tag(tags)

        md5 = Hash.get_or_create(value=item['md5'])

        f_hyb.active_link_to(md5, 'md5', self.name)

        sha1 = Hash.get_or_create(value=item['sha1'])

        f_hyb.active_link_to(sha1, 'sha1', self.name)

        if 'domains' in item:
            for domain in item['domains']:
                try:
                    new_host = Hostname.get_or_create(value=domain)
                    f_hyb.active_link_to(new_host, 'C2', self.name)
                    logging.debug(domain)

                    new_host.add_context({'source': self.name, 'contacted by': f_hyb})
                except ObservableValidationError as e:
                    logging.error(e)

        if 'extracted_files' in item:
            for extracted_file in item['extracted_files']:
                context_file_dropped = {'source': self.name}

                if not 'sha256' in extracted_file:
                    logging.error(extracted_file)
                    continue

                new_file = File.get_or_create(value='FILE: {}'.format(extracted_file['sha256']))
                sha256_new_file = Hash.get_or_create(value=extracted_file['sha256'])
                new_file.active_link_to(sha256_new_file, 'sha256', self.name)

                context_file_dropped['virustotal_score'] = 0
                context_file_dropped['size'] = extracted_file['file_size']

                if 'av_matched' in extracted_file:
                    context_file_dropped['virustotal_score'] = extracted_file['av_matched']

                if 'threatlevel_readable' in extracted_file:
                    context_file_dropped['threatlevel'] = extracted_file['threatlevel_readable']

                if 'av_label' in extracted_file:
                    new_file.tag(extracted_file['av_label'])

                if 'type_tags' in extracted_file:
                    new_file.tag(extracted_file['type_tags'])

                new_file.add_context(context_file_dropped)

                f_hyb.active_link_to(new_file, 'drop', self.name)